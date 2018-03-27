#!/usr/bin/env python

# Copyright 2017 Univa Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import struct
import socket
import re
import time
import gevent
import uuid
import os
import base64
import copy
from gevent import lock

import platform
if platform.system() == "Linux":
    import gevent_inotifyx as inotify
from collections import namedtuple

from urb.messaging.message_handler import MessageHandler
from urb.messaging.channel_factory import ChannelFactory
from urb.messaging.messaging_utility import MessagingUtility
from urb.adapters.adapter_manager import AdapterManager
from urb.utility.naming_utility import NamingUtility
from urb.utility.utils import isfloat
from urb.messaging.mesos.resource_offers_message import ResourceOffersMessage
from urb.messaging.mesos.register_framework_message import RegisterFrameworkMessage
from urb.messaging.mesos.reregister_framework_message import ReregisterFrameworkMessage
from urb.messaging.mesos.unregister_framework_message import UnregisterFrameworkMessage
from urb.messaging.mesos.framework_registered_message import FrameworkRegisteredMessage
from urb.messaging.mesos.framework_reregistered_message import FrameworkReregisteredMessage
from urb.messaging.mesos.register_executor_runner_message import RegisterExecutorRunnerMessage
from urb.messaging.mesos.register_executor_message import RegisterExecutorMessage
from urb.messaging.mesos.executor_registered_message import ExecutorRegisteredMessage
from urb.messaging.mesos.reregister_executor_message import ReregisterExecutorMessage
from urb.messaging.mesos.executor_reregistered_message import ExecutorReregisteredMessage
from urb.messaging.mesos.launch_tasks_message import LaunchTasksMessage
from urb.messaging.mesos.run_task_message import RunTaskMessage
from urb.messaging.mesos.status_update_message import StatusUpdateMessage
from urb.messaging.mesos.status_update_acknowledgement_message import StatusUpdateAcknowledgementMessage
from urb.messaging.mesos.executor_to_framework_message import ExecutorToFrameworkMessage
from urb.messaging.mesos.framework_to_executor_message import FrameworkToExecutorMessage
from urb.messaging.mesos.shutdown_executor_message import ShutdownExecutorMessage
from urb.messaging.mesos.kill_task_message import KillTaskMessage
from urb.messaging.mesos.reconcile_tasks_message import ReconcileTasksMessage
from urb.messaging.mesos.revive_offers_message import ReviveOffersMessage
from urb.messaging.mesos.rescind_resource_offer_message import RescindResourceOfferMessage
from urb.messaging.service_disconnected_message import ServiceDisconnectedMessage
from urb.messaging.slave_shutdown_message import SlaveShutdownMessage

from urb.service.job_monitor import JobMonitor
from urb.service.channel_monitor import ChannelMonitor
from urb.service.retry_manager import RetryManager
from urb.utility.framework_tracker import FrameworkTracker
from urb.utility.resource_tracker import ResourceTracker
from urb.utility.value_utility import ValueUtility
from urb.utility.port_range_utility import PortRangeUtility
from urb.config.config_manager import ConfigManager
from urb.log.log_manager import LogManager
from urb.db.db_manager import DBManager

from urb.service.mesos_http import MesosHttp
from urb.service.slave_http import SlaveHttp

from urb.exceptions.registration_error import RegistrationError
from urb.exceptions.unknown_job import UnknownJob
from urb.exceptions.completed_job import CompletedJob


class MesosHandler(MessageHandler):

    CHANNEL_DELETE_WAIT_PERIOD_IN_SECONDS = 10
    MISSING_FRAMEWORK_WAIT_PERIOD_IN_SECONDS = 120
    DEFAULT_FRAMEWORK_OFFER_WAIT_PERIOD_IN_SECONDS = 10
    FRAMEWORK_OFFER_MIN_WAIT_IN_SECONDS = 1
    MAX_NUMBER_OF_FINISHED_FRAMEWORKS = 25
    SLAVE_GRACE_PERIOD = 120
    DEFAULT_FRAMEWORK_MAX_TASKS = 10
    # Actual Mesos version has to be set by the build procedure
    MESOS_VERSION = "1.4.0"

    def __init__(self, channel_name, initial_retry_interval, max_retry_count):
        MessageHandler.__init__(self, channel_name)
        self.logger.debug("Getting AdapterManager: name=%s, channel_name=%s" % (self.name, channel_name))
        self.adapter = AdapterManager.get_instance().get_adapter(self.name, channel_name)
        self.__master_broker = False
        self.retry_manager = RetryManager(self.channel, initial_retry_interval, max_retry_count)
        self.__scheduled_shutdowns = {}
        #self.__finished_frameworks = deque([],MesosHandler.MAX_NUMBER_OF_FINISHED_FRAMEWORKS)
        self.framework_db_interface = DBManager.get_instance().get_framework_db_interface()
        self.event_db_interface = DBManager.get_instance().get_event_db_interface()
        self.__DeleteElement = namedtuple('DeleteElement',['dict','key'])
        self.__delete_elements = []
        self.__new_framework_lock = lock.RLock()
        self.configure()
        if platform.system() == "Linux":
            gevent.spawn(self.__watch_config)
        self.service_hostname = socket.gethostname()
        self.http_service = MesosHttp(self.scheduler_http_port) if self.http_enabled else None
        self.slave_http_service = SlaveHttp(self.executor_http_port) if self.http_service else None

    def configure(self):
        cm = ConfigManager.get_instance()
        default_config_file = cm.get_config_file()
        self.executor_runner_config_file = cm.get_config_option('MesosHandler',
            'executor_runner_config_file')
        if not self.executor_runner_config_file:
            self.executor_runner_config_file = default_config_file
            self.logger.warn('Could not find executor_runner_config_file option in config file %s' % default_config_file)
        else:
            if not os.path.dirname(self.executor_runner_config_file):
                self.executor_runner_config_file = os.path.join(os.path.dirname(default_config_file), os.path.basename(self.executor_runner_config_file))

        if not os.path.exists(self.executor_runner_config_file):
            self.logger.warn('Could not find executor runner config file %s, falling back to default %s' % (self.executor_runner_config_file, default_config_file))
            self.executor_runner_config_file = default_config_file
        self.logger.debug('Executor runner config file is set to %s' % (self.executor_runner_config_file))
        self.http_enabled = cm.get_config_option("Http", "enabled", True)
        if self.http_enabled:
            scheduler_http_port = cm.get_config_option("Http", "scheduler_port")
            if not scheduler_http_port:
                self.logger.warn("Could not get scheduler http port from configuration file, defaulting to port 5050")
                self.scheduler_http_port = 5050
            else:
                self.scheduler_http_port = int(scheduler_http_port)
            interval = cm.get_config_option("Http", "heartbeat_interval_seconds")
            if not interval:
                self.logger.warn("Could not get heartbeat interval from configuration file, defaulting to port 15 seconds")
                self.heartbeat_interval = 15
            else:
                self.heartbeat_interval = int(interval)
            executor_http_port = cm.get_config_option("Http", "executor_port")
            if not executor_http_port:
                self.logger.warn("Could not get executor http port from configuration file, defaulting to port 5051")
                self.executor_http_port = 5051
            else:
                self.executor_http_port = int(executor_http_port)
        else:
            self.logger.info("HTTP API disabled")

    def __watch_config(self):
        # IN_CLOSE_WRITE handles completion of the config file modification
        # IN_DELETE_SELF handles k8s case of the configmap midification
        mask = inotify.IN_CLOSE_WRITE|inotify.IN_DELETE_SELF
        nfd = inotify.init()
        wfd = inotify.add_watch(nfd, ConfigManager.get_instance().get_config_file(), mask)
        self.logger.info("Watching for URB configuration changes")
        # wait for config file change
        while True:
            self.logger.info("Waiting for URB configuration change events")
            events = inotify.get_events(nfd)
            self.logger.info("URB configuration changes: events: %s" % events)
            for ev in set(events):
                self.logger.info("Config event: %s" % ev)
                if ev.mask & inotify.IN_CLOSE_WRITE:
                    self.__reload_config()
                if ev.mask & inotify.IN_DELETE_SELF:
                    # give some time for new file to be created
                    gevent.sleep(1)
                    self.__reload_config()
                    # watch new file
                    wfd = inotify.add_watch(nfd, ConfigManager.get_instance().get_config_file(), mask)
                else:
                    self.logger.info("Do not reload config for above event")
            gevent.sleep(1)

    def __reload_config(self):
        cm = ConfigManager.get_instance()
        lm = LogManager.get_instance()
        cm.clear_config_parser()
        level = cm.get_config_option("ConsoleLogging", "level")
        # set new log levels
        self.logger.info("Console log level: %s" % level)
        lm.set_console_log_level(level)
        level = cm.get_config_option("FileLogging", "level")
        self.logger.info("File log level: %s" % level)
        lm.set_file_log_level(level)
        self.logger.info("Frameworks in list: %s" % FrameworkTracker.get_instance().keys())
        for framework in FrameworkTracker.get_instance().keys():
            val = FrameworkTracker.get_instance().get_active_or_finished_framework(framework)
            if val is not None:
                self.logger.info("Reconfigure framework: %s" % framework)
                self.configure_framework(val)
        self.adapter.config_update()

    def get_scheduler_http_port(self):
        return self.scheduler_http_port

    def get_executor_http_port(self):
        return self.executor_http_port

    def get_heartbeat_interval(self):
        return self.heartbeat_interval

    def get_target_preprocessor(self, target):
        if self.event_db_interface is not None and self.event_db_interface.is_active():
            return self.update_event_db
        return None

    def get_target_executor(self, target):
        supported_target_dict = {
            'AuthenticateMessage' : self.authenticate,
            'DeactivateFrameworkMessage' : self.deactivate_framework,
            'ExitedExecutorMessage' : self.exited_executor,
            FrameworkToExecutorMessage.target() : self.framework_to_executor,
            ExecutorToFrameworkMessage.target() : self.executor_to_framework,
            KillTaskMessage.target() : self.kill_task,
            LaunchTasksMessage.target() : self.launch_tasks,
            ReconcileTasksMessage.target() : self.reconcile_tasks,
            RegisterExecutorMessage.target() : self.register_executor,
            ReregisterExecutorMessage.target() : self.reregister_executor,
            RegisterExecutorRunnerMessage.target() : self.register_executor_runner,
            RegisterFrameworkMessage.target() : self.register_framework,
            'RegisterSlaveMessage' : self.register_slave,
            ReregisterFrameworkMessage.target() : self.reregister_framework,
            'ReregisterSlaveMessage' : self.reregister_slave,
            'ResourceRequestMessage' : self.resource_request,
            ReviveOffersMessage.target() : self.revive_offers,
            StatusUpdateAcknowledgementMessage.target() : self.status_update_acknowledgement,
            StatusUpdateMessage.target() : self.status_update,
            'SubmitSchedulerRequest' : self.submit_scheduler_request,
            UnregisterFrameworkMessage.target() : self.unregister_framework,
            'UnregisterSlaveMessage' : self.unregister_slave,
        }
        return supported_target_dict.get(target)

    def get_target_postprocessor(self, target):
        # We must always post process target to release framework lock
        return self.__target_postprocessor

    # Implement the post processor interface
    def __target_postprocessor(self,request):
        # First call the DB post processor, which returns framework id
        # associated with request
        framework_id = self.update_framework_db(request)
        framework = FrameworkTracker.get_instance().get_active_or_finished_framework(framework_id)

        # Now clean up deleted objects
        for de in self.__delete_elements:
            if de.dict.has_key(de.key):
                self.logger.debug("Deleting key %s from dict %s" % (de.key, "%x" % id(de.dict)))
                del de.dict[de.key] 
            else:
                self.logger.warn("Unable to delete missing key %s from dict %s" % (de.key, "%x" % id(de.dict))) 

        # Reset the delete_elements to []
        self.__delete_elements = []

        # Release lock
        self.__release_framework_lock(framework)

    def __acquire_framework_lock(self, framework, blocking=True):
        if framework is None:
            self.logger.warn('Framework is None, cannot acquire lock')
            return False

        framework_lock = framework.get('lock')
        framework_id = framework.get('id')
        # An unsync'ed get is OK here because we make sure only one could be created
        if framework_lock is None:
            # We need to get our global lock to make sure we only make one framework lock
            result = self.__new_framework_lock.acquire(blocking)
            if result:
                # Now check and see if it was created by someone else
                if not framework.get('lock'):
                    # Still not created...create it!
                    framework['lock'] = lock.RLock()
                    self.logger.debug('Created lock for framework id %s' % framework_id['value'])
                self.__new_framework_lock.release()
            else:
                self.logger.warn('Failed to acquire new_framework_lock for framework id %s' % framework_id['value'])
            framework_lock = framework.get('lock')

        # If we don't have a framework_lock set here that means a lock couldn't be created.
        if not framework_lock:
            self.logger.warn("Unable to load or create framework lock for framework id %s" % framework_id['value'])
            return False

        self.logger.debug('Acquiring lock for framework id %s' % framework_id['value'])
        result = framework_lock.acquire(blocking)
        if result:
            self.logger.debug('Acquired lock for framework id %s' % framework_id['value'])
            framework['lock_acquired'] = True
        else:
            self.logger.warn('Failed to acquire lock for framework id %s' % framework_id['value'])
        return result

    def __release_framework_lock(self, framework):
        if framework is None:
            self.logger.warn('Framework is None, cannot release lock')
            return

        framework_lock = framework.get('lock')
        framework_id = framework.get('id')
        if not framework.get('lock_acquired'):
            self.logger.debug('Tried to release non-acquired lock for framework id %s' % framework_id['value'])
            return
  
        if framework_lock is not None:
            self.logger.debug('Releasing lock for framework id %s' % framework_id['value'])
            framework['lock_acquired'] = False
            framework_lock.release()
            self.logger.debug('Released lock for framework id %s' % framework_id['value'])
        else:
            self.logger.debug("Releasing framework lock: no framework lock")
    
    def __add_delete_element(self, d, k):
        self.__delete_elements.append(self.__DeleteElement(d,k))

    def elected_master_callback(self):
        self.logger.debug('Elected master callback')
        self.__master_broker = True
        self.channel.start_listener()

        # Start monitors
        self.job_monitor = JobMonitor(self.adapter,
            self.update_job_status, self.delete_job, self.update_job_accounting)
        self.job_monitor.start()
        self.channel_monitor = ChannelMonitor(self.validate_channel, self.delete_channel)
        self.channel_monitor.start()
        self.retry_manager.start()
        if self.http_service:
            self.http_service.start(self)
            self.slave_http_service.start(self)

        # Notify existing channels we restarted
        self.send_service_disconnected_message()

    def demoted_callback(self):
        self.logger.debug('We are no longer the master')
        # Trigger a shutdown of the offer loop
        self.__master_broker = False
        if self.http_service:
            self.http_service.stop()
            self.slave_http_service.stop()
        self.channel.stop_listener()
        self.job_monitor.stop()
        self.channel_monitor.stop()
        self.retry_manager.stop()

    # Need to override listen so that we don't start listening when we aren't the master
    def listen(self):
        if self.__master_broker:
            return self.channel.start_listener()
        else:
            return None

    def update_job_status(self, job_id, framework_id, job_status):
        self.logger.debug("Updating job status for framework %s and job id %s" % (framework_id, job_id))
        framework = FrameworkTracker.get_instance().get_active_or_finished_framework(framework_id)
        if framework is not None:
            # No need to acquire/release lock here
            existing_statuses = framework.get('job_statuses',{})
            existing_statuses[job_id] = job_status
            self.logger.trace("Existing job statuses: %s, new: %s" % (existing_statuses, job_status))
            framework['job_statuses'] = existing_statuses
        else:
            self.logger.debug("Cannot update job status. Framework does not exist for id: %s" % framework_id)

    def update_job_accounting(self, job_id, framework_id, job_accounting):
        self.logger.debug('Updating accounting for framework %s and job id %s' % (framework_id, job_id))
        framework = FrameworkTracker.get_instance().get_active_or_finished_framework(framework_id)
        if framework is not None:
            # No need to acquire/release lock here
            existing_accounting = framework.get('job_accounting',{})
            existing_accounting[job_id] = job_accounting
            self.logger.trace("Existing job accounting: %s, new: %s" % (existing_accounting, job_accounting))
            framework['job_accounting'] = existing_accounting

            # Make sure db gets updated here
            if self.framework_db_interface is not None and self.framework_db_interface.is_active():
                self.framework_db_interface.update_framework(framework_id)
        else:
            self.logger.debug("Cannot update accounting info. Framework does not exist for id: %s" % framework_id)

    def __delete_slave(self, framework, slave):
        # Delete the slave
        self.logger.debug('Deleting slave %s' % slave)
        self.__add_delete_element(framework['slave_dict'], slave['id']['value'])
        slave_channel = slave['channel']
        slave['offerable'] = False
        if slave.has_key('placeholder'):
            try:
                del framework['placeholder_to_slave'][slave['placeholder']]
            except Exception, ex:
                self.logger.warn("Unable to delete placholder_to_slave item: %s" % slave['placeholder'])
                self.logger.debug("Placeholder map: %s" % framework.get('placeholder_to_slave'))
                self.logger.debug(ex)
        self.update_completed_executor_summary_db(slave)
        self.__delete_channel_with_delay(slave_channel.name)

    def delete_job(self, job_id, framework_id):
        self.logger.debug('Deleting job id %s for framework id %s' % (job_id, framework_id))
        framework = FrameworkTracker.get_instance().get_active_or_finished_framework(framework_id)
        if framework is None:
            self.logger.debug('Framework id %s could not be found' % (framework_id))
            return

        # Acquire framework lock
        self.__acquire_framework_lock(framework)

        # We need to clean up any slaves that were created for this job
        slave_prefix = NamingUtility.create_slave_id(job_id,"undefined","")
        self.logger.debug("Looking for slaves that start with: %s" % slave_prefix)
        for k,v  in framework.get('slave_dict',{}).iteritems():
            if k.startswith(slave_prefix):
                self.__delete_slave(framework, v)
        self.logger.debug("Done looking for slaves that start with: %s" % slave_prefix)
        try:
            if framework is not None and framework.has_key('job_ids'):
                self.logger.debug('Removing job id %s from framework jobs: %s' %
                                  (job_id, framework.get('job_ids')))
                # Job may have tasks, in which case the line below will fail
                # with a key error
                #framework['job_ids'].remove((job_id,None,None))
                job_id_tuple = None
                for jid in framework.get('job_ids'):
                   if jid[0] == job_id:
                       job_id_tuple = jid
                if job_id_tuple is not None:
                    self.logger.debug("Removing job id %s from framework jobs with key: %s" % (job_id, job_id_tuple))
                    framework['job_ids'].remove(job_id_tuple)
                else:
                    self.logger.error('Could not remove job id %s from framework jobs: %s' %
                                      (job_id, framework.get('job_ids')))
                
                       
                self.logger.debug('Looking for tasks with job id: %s to mark lost' % job_id)
                task_dict = framework.get('task_dict',{})
                for task_id, task in task_dict.items():
                    if task.get('job_id') == job_id:
                        #Scheduler gets the task update, send shutdown to the executor
                        self.logger.debug('About to process task lost for job id %s' % job_id)
                        self.__process_task_lost_status_update(task['task_info'], framework, task['task_info'].get('slave_id'))

                # remove job status
                #self.logger.debug("Removing job status for %s" % job_id)
                #statuses = framework.get('job_statuses',{})
                #if job_id in statuses:
                #    del statuses[job_id]

        finally:
            # Release lock
            self.__release_framework_lock(framework)
                    
    def disconnect_channel(self, channel_id):
        cf = ChannelFactory.get_instance()
        message = ServiceDisconnectedMessage(self.channel.name, {})
        channel = cf.create_channel(channel_id)
        channel.write(message.to_json())

    def validate_channel(self, channel_id, channel_info):
        # Lets make sure we know about this framework
        framework_id = channel_info.get('framework_id')
        framework = FrameworkTracker.get_instance().get(framework_id)
        if framework is None:
            if not FrameworkTracker.get_instance().is_framework_finished(framework_id):
                #  Send disconnect message...
                self.disconnect_channel(channel_id)
                self.logger.debug('Validating channel, sending service disconnected message to %s at %s' %
                    (channel_info.get('endpoint_type','unknown endpoint type'),channel_id))
            else:
                self.logger.debug("Validating channel, framework %s is already finished, do not send service disconnected" %
                                  framework_id)
        elif channel_info.get('endpoint_type') == 'executor_runner':
            # Slave message... make sure we know about it...
            slave = framework.get('slave_dict',{}).get(channel_info.get('slave_id'))
            if not slave:
                self.disconnect_channel(channel_id)
                self.logger.debug('Validating channel, sending service disconnected message to slave at %s' %
                   channel_id)
        elif channel_info.get('endpoint_type') == 'executor':
            # Executors have slave and executor info
            slave = framework.get('slave_dict',{}).get(channel_info.get('slave_id'))
            if not slave or not slave.has_key('executor_channel'):
                self.disconnect_channel(channel_id)
                self.logger.debug('Validating channel, sending service disconnected message to executor at %s' %
                    channel_id)

    def delete_channel(self, channel_id, channel_info):
        cf = ChannelFactory.get_instance()
        framework_id = channel_info.get('framework_id')
        if framework_id is None or not channel_info.has_key('endpoint_type'):
            self.logger.debug('Deleting orphan channel id %s' % (channel_id))
            cf.destroy_channel(channel_id)
        else:
            framework = FrameworkTracker.get_instance().get(channel_info['framework_id'])
            if framework is None:
                self.logger.debug(
                    'Deleting channel %s for unknown framework id %s' %
                    (channel_id, framework_id))
                cf.destroy_channel(channel_id)
                return
            if channel_info.get('endpoint_type') == 'framework':
                # This is a scheduler channel but it may not be the 'active'
                # scheduler channel... lets check
                if framework['channel_name'] == channel_id:
                    # This is the active scheduler channel, destroy framework...
                    self.logger.debug(
                        'Deleting channel %s and framework %s' %
                        (channel_id, framework_id))
                    self.__delete_framework(framework_id)
                else:
                    # This is not the active scheduler channel we should keep the
                    # framework around.  Still need to delete the channel though
                    self.logger.debug(
                        'Deleting orphan channel %s for framework id %s' %
                        (channel_id, framework_id))
                    cf.destroy_channel(channel_id)

    def __generate_offers_for_framework(self, framework, http = False):
        # First we need to see if we have any slaves around...
        slaves = []
        offers = []
        slave_dict = framework.get("slave_dict", {})
        slaves.extend(slave_dict.values())
        slaves_cnt = len(slaves)
        framework_config = framework.get('config')
        max_tasks = int(framework_config.get('max_tasks'))

        self.logger.debug("Generating offers for framework %s with %d slaves: %s" %
                         (framework['name'], slaves_cnt, [sl['id']['value'] for sl in slaves]))
        now = time.time()
        built_offer_count = 0
        offerable_after_for_placeholder = 0
        for slave in slaves:
            offerable_after = slave.get('offerable_after', 0)
            offerable = ( slave.get('offerable',True) and (not slave.get('is_command_executor',False)) and (now > offerable_after) )
            self.logger.debug("Slave %s: offerable=%s, is_command_executor=%s, now-offerable_after=%s, offerable_after_for_placeholder=%s" %
                               (slave['id']['value'], slave.get('offerable',True), slave.get('is_command_executor',False),
                               (now - offerable_after), offerable_after_for_placeholder))
            if offerable:
                self.logger.debug("Generating offer for framework %s from slave %s" % (framework['name'], slave))
                offer = self.__build_offer(framework, slave, http=http)
                self.logger.debug("Generated offer: %s" % offer)

                if offer is not None:
                    # Don't offer for this slave again
                    self.logger.debug("Appending and disabling offers for slave: %s" % slave['id']['value'])
                    slave['offerable'] = False
                    offers.append(offer)
                    built_offer_count += 1
            else:
                if offerable_after > offerable_after_for_placeholder:
                    offerable_after_for_placeholder = offerable_after
                self.logger.debug("Skipping offer for framework %s from not offerable slave: %s" % (framework['name'], slave))

#        built_offer_count = len(offers)
        self.logger.debug("Offers built for framework [%s]: %d" %(framework["name"], built_offer_count))
        # Only send placeholder offers if we have no other offers to send, we are under our max offer count
        # and we don't have any pending jobs
        if built_offer_count == 0 and slaves_cnt < max_tasks:
            # Pending job count can be determined by the difference between the len job_id and slave_dict
            pending_jobs = len(framework.get('job_ids',[])) - slaves_cnt
            self.logger.debug("Framework %s has %s pending job(s) (active jobs: %s)" % \
                              (framework["name"], pending_jobs, framework.get('job_ids',[])))
#            if pending_jobs <= 0 and framework.get('__placeholder_offerable_after',0) < now:
            if pending_jobs <= 0:
                self.logger.trace("Framework placeholder_offerable_after=%s, offerable_after_for_placeholder=%s" %
                                  (framework.get('__placeholder_offerable_after', 0),offerable_after_for_placeholder))
                if offerable_after_for_placeholder != 0 and \
                   offerable_after_for_placeholder < framework.get('__placeholder_offerable_after', 0):
                    framework['__placeholder_offerable_after'] = offerable_after_for_placeholder
                if framework.get('__placeholder_offerable_after',0) < now:
                    dummy_count = int(framework_config.get('initial_tasks',1)) if framework_config else 1
                    for i in range(0,dummy_count):
                        # for http framework use actual service host name so it can response to operator API
                        # requests with some dummy data
                        dummy_slave = {
                            "hostname" : self.service_hostname if http else "place-holder",
                            "id" : { "value" : "place-holder"},
                            'offerable' : True
                            }
                        self.__initialize_slave_resources(framework, dummy_slave)
                        self.logger.debug("Adding placeholder offer: %s" % dummy_slave)
                        offers.append(self.__build_offer(framework, dummy_slave, force=True, http=http))
                        built_offer_count +=1
                else:
                    self.logger.debug("Do not add placeholder offer: offerable after: %s" %
                                      framework.get('__placeholder_offerable_after',0))
            else:
                self.logger.debug("Do not add placeholder offer: there are pending jobs")

        # If we have some offers to send for this framework we can send them now
        if built_offer_count > 0:
            if http:
                return offers
            else:
                self.send_offers(framework, offers)

    def __generate_offers(self, framework_id):
        framework = FrameworkTracker.get_instance().get(framework_id['value'])
        offer_event = framework.get('offer_event')
        self.logger.info("Starting offer loop for framework id %s with offer event %s" % (framework_id['value'], offer_event))
        while True:
            try:
                framework = FrameworkTracker.get_instance().get(framework_id['value'])
                if framework is None:
                    if self.framework_db_interface is not None and self.framework_db_interface.is_active():
                        self.framework_db_interface.set_framework_summary_status_inactive(framework_id['value'])
                    self.logger.info("Framework id %s is not active, exiting offer loop" % framework_id['value'])
                    break

                # Make sure we don't thrash
                last_offer_time = framework.get("__last_offer_time",0)
                current_time = time.time()
                seconds_since_last_offer = current_time - last_offer_time
                if seconds_since_last_offer < MesosHandler.FRAMEWORK_OFFER_MIN_WAIT_IN_SECONDS:
                    time_to_sleep = MesosHandler.FRAMEWORK_OFFER_MIN_WAIT_IN_SECONDS - seconds_since_last_offer
                    self.logger.debug("Accelerated offer, waiting %s second(s)" % time_to_sleep)
                    gevent.sleep(time_to_sleep)
                    current_time = time.time()
                framework['__last_offer_time'] = current_time

                if not self.__master_broker:
                    # In case we need to restart when we reregister,
                    # remove offer event
                    self.logger.debug("No master broker")
                    if framework.has_key('offer_event'):
                        self.logger.debug("Deleting offer event: %s" % framework['offer_event'])
                        del framework['offer_event']
                    break

                offer_event.clear()
                # Acquire framework lock
                self.__acquire_framework_lock(framework)

                # Read our current iterations wait time
                next_offer_time = framework.get('__next_offer_time',0)
                if current_time < next_offer_time:
                    time_to_wait = next_offer_time - current_time
                else:
                    time_to_wait = framework['config']['offer_period']
                framework['__next_offer_time'] = 0
                try:
                    offers = self.__generate_offers_for_framework(framework)
                    self.logger.debug("After __generate_offers_for_framework")
                except Exception as e:
                    self.logger.error("Offers not generated: %s" % e)
                finally:
                    # Release lock
                    self.logger.debug("In finally before release lock")
                    self.__release_framework_lock(framework)
                self.logger.debug("Waiting in offer loop for framework id %s for %s sec" % (framework_id['value'], time_to_wait))
                offer_event.wait(time_to_wait)
                self.logger.debug("event triggered")
            except Exception, ex:
                self.logger.error("Exception in offer loop for framework id %s" % framework_id['value'])
                self.logger.exception(ex)
        self.logger.info("Exiting offer loop for framework id %s" % framework_id['value'])

    def http_generate_offers(self, framework_id):
        self.logger.info("HTTP: Starting offer loop for framework id %s" % framework_id['value'])
#        framework = FrameworkTracker.get_instance().get(framework_id['value'])
        last_heartbeat_time = time.time()
#        framework['offer_event'] = gevent.event.AsyncResult()
#        offer_event = framework.get('offer_event')
        while True:
            try:
                framework = FrameworkTracker.get_instance().get(framework_id['value'])
                if framework is None:
                    if self.framework_db_interface is not None and self.framework_db_interface.is_active():
                        self.framework_db_interface.set_framework_summary_status_inactive(framework_id['value'])
                    self.logger.info("Framework id %s is not active, exiting offer loop" % framework_id['value'])
                    break

                if not self.__master_broker:
                    # In case we need to restart when we reregister,
                    # remove offer event
                    self.logger.debug("No master broker, exiting offer loop")
                    if framework.has_key('offer_event'):
                        self.logger.debug("Deleting offer event: %s" % framework['offer_event'])
                        del framework['offer_event']
                    break
                self.logger.debug("In offer loop for framework %s with offer event %s" % (framework_id['value'], repr(framework['offer_event'])))

                last_offer_time = framework.get("__last_offer_time", 0)
                current_time = time.time()
                since_last_offer = current_time - last_offer_time

                # Acquire framework lock
#                self.__acquire_framework_lock(framework)
                self.logger.debug("Renew scheduler AsyncResult, old=%s" % repr(framework['offer_event']))
                if 'offer_event' in framework:
                    del framework['offer_event']
                framework['offer_event'] = gevent.event.AsyncResult()
                self.logger.debug("New scheduler AsyncResult=%s" % repr(framework['offer_event']))

                self.__acquire_framework_lock(framework)

                # Read our current iterations wait time
                next_offer_time = framework.get('__next_offer_time',0)
                if current_time < next_offer_time:
                    time_to_wait = next_offer_time - current_time
                    self.logger.debug("HTTP event loop: accelerated offer: next_offer_time=%d" % next_offer_time)
                else:
                    time_to_wait = framework['config']['offer_period']
                self.logger.debug("HTTP event loop: current_time=%d, last_offer_time=%d, since_last_offer=%d, time_to_wait=%d" %
                                  (current_time, last_offer_time, since_last_offer, time_to_wait))
                framework['__next_offer_time'] = 0

                if current_time - last_heartbeat_time >= self.heartbeat_interval:
                    last_heartbeat_time = current_time
                    self.logger.debug("Before yield heartbeat")
                    hb = {'type' : 'HEARTBEAT'}
                    yield hb
                    self.logger.debug("After yield heartbeat")

                try:
                    if since_last_offer >= time_to_wait:
                        offers = self.__generate_offers_for_framework(framework, True)
                        self.logger.debug("After __generate_offers_for_framework")
                        if offers and len(offers) > 0:
                            self.logger.debug("Before yield offers")
                            offers_resp = {
                                'type' : 'OFFERS',
                                'offers' : { 'offers' : offers }
                            }
                            yield offers_resp
                            self.logger.debug("After yield offers")
                        else:
                            self.logger.debug("Skip empty offers")
                    framework['__last_offer_time'] = current_time
                except Exception as e:
                    self.logger.error("Offers not generated: %s" % e)
                finally:
                    # Release lock
                    self.logger.debug("In finally before release lock")
                    self.__release_framework_lock(framework)

                self.logger.debug("Waiting for event %s, framework id %s for max %s sec" % (repr(framework['offer_event']), framework_id['value'], time_to_wait))
                framework['offer_event'].wait(time_to_wait)
                data = framework['offer_event'].value
                self.logger.debug("event: %s, event data=%s" % (repr(framework['offer_event']), data))
                if data:
                    yield data
                    self.logger.debug("After yielded data")

#                self.logger.debug("Renew scheduler AsyncResult, old=%s" % repr(framework['offer_event']))
#                self.__acquire_framework_lock(framework)
#                del framework['offer_event']
#                framework['offer_event'] = gevent.event.AsyncResult()
#                self.__release_framework_lock(framework)
#                self.logger.debug("New scheduler AsyncResult=%s" % repr(framework['offer_event']))
            except Exception, ex:
                self.logger.error("Exception in offer loop for framework id %s" % framework_id['value'])
                self.logger.exception(ex)
        self.logger.info("Exiting offer loop for framework id %s" % framework_id['value'])


    def authenticate(self, request):
        self.logger.info('Authenticate: %s' % request)
        self.adapter.authenticate(request)
        return None, None

    def deactivate_framework(self, request):
        self.logger.info('Deactivate framework: %s' % request)
        self.adapter.deactivate_framework(request)
        return None, None

    def exited_executor(self, request):
        self.logger.info('Exited executor: %s' % request)
        self.adapter.exited_executor(request)
        return None, None

    def http_message(self, framework_id, agent_id, executor_id, data):
        payload = {
            'mesos.internal.FrameworkToExecutorMessage' : {
                'framework_id' : framework_id,
                'agent_id' : agent_id,
                'executor_id' : executor_id,
                'data' : data
             }
        }
        request = {
            'source_id' : None, # indicate http type
            'payload_type' : 'json',
            'ext_payload' : None,
            'payload' : payload
            }
        framework, _ = self.framework_to_executor(request)
        if framework:
            self.__release_framework_lock(framework)

    def framework_to_executor(self, request):
        self.logger.info('Framework to executor: %s' % request)
        message = request.get('payload', {}).get('mesos.internal.FrameworkToExecutorMessage')
        if not message:
            self.logger.warn("Framework to executor: empty message")
            return None, None
        framework_id = message['framework_id']
        framework = FrameworkTracker.get_instance().get_framework_and_store_request_framework_id(request, framework_id['value'])
       
        # Acquire framework lock
#        self.__acquire_framework_lock(framework)
        
#        should_retry = True
        if framework:
            http = True if framework['channel_name'] == "http" else False
            if http:
                http_resp = {
                    'type' : 'MESSAGE',
                    'message' : { 'data' : message['data'] }
                }
                agent_id_value = message['agent_id']['value']
                if agent_id_value.startswith("place-holder"):
                    agent_id_value = framework.get('placeholder_to_slave',{}).get(agent_id_value)
                slave = framework.get('slave_dict',{}).get(agent_id_value)
                ar = slave.get('async_result')
                self.logger.debug("Setting slave AsyncResult: %s" % repr(ar))
                ar.set(http_resp)
                gevent.sleep(0)
            else:
                should_retry = True
                # Acquire framework lock
                self.__acquire_framework_lock(framework)
                should_retry = not self.send_framework_message(framework, message)
                if should_retry:
                    self.logger.warn("Received message from unknown framework or to unknown executor: %s", framework_id['value'])
                    self.retry_manager.retry(request)
                return framework, None

#        if should_retry:
#            self.logger.warn("Received message from unknown framework or to unknown executor: %s", framework_id['value'])
#            self.retry_manager.retry(request)

        return None, None

    def executor_to_framework(self, request):
        self.logger.info('Executor to framework: %s' % request)
        message = request.get('payload', {}).get('mesos.internal.ExecutorToFrameworkMessage')
        if not message:
            self.logger.warn("Executor to framework: empty message")
            return None, None
        framework_id = message['framework_id']
        framework = FrameworkTracker.get_instance().get_framework_and_store_request_framework_id(request, framework_id['value'])
        
        if framework:
            http = True if framework['channel_name'] == "http" else False
            if http:
                # framework id is not a part of the message
                if 'framework_id' in message:
                    del message['framework_id']
                # there is no way to get agent_id from framework while executor_id is not unique
                #if 'agent_id' is not in message:
                #    framework
                http_resp = {
                    'type' : 'MESSAGE',
                    'message' : message
                }
                offer_event = framework.get('offer_event')
                self.logger.debug("Setting AsyncResult: %s" % repr(offer_event))
                offer_event.set(http_resp)
                gevent.sleep(0)
            else:
                # Acquire framework lock
                self.__acquire_framework_lock(framework)
                self.send_executor_message(framework, message)
                return framework, None
        else:
            self.logger.warn("Received message to unknown framework: %s", framework_id['value'])
            self.retry_manager.retry(request)

        return None, None

    #def executor_to_framework(self, request):
        #self.logger.info('Executor to framework: %s' % request)
        #message = request.get('payload', {}).get('mesos.internal.ExecutorToFrameworkMessage')
        #if not message:
            #self.logger.warn("Executor to framework: empty message")
            #return None, None
        #framework_id = message['framework_id']
        #framework = FrameworkTracker.get_instance().get_framework_and_store_request_framework_id(request, framework_id['value'])
#!!! may be no need to lock for http????
        ## Acquire framework lock
        #self.__acquire_framework_lock(framework)

        #if framework:
            #http = True if framework['channel_name'] == "http" else False
            #if http:
                ## framework id is not a part of the message
##                if 'framework_id' in message:
##                    del message['framework_id']
                #http_resp = {'type' : 'MESSAGE',
                            #'message' : message}
                #offer_event = framework.get('offer_event')
                #self.logger.debug("Setting AsyncResult: %s" % repr(offer_event))
                #offer_event.set(http_resp)
                #gevent.sleep(0)
            #else:
                #self.send_executor_message(framework, message)
        #else:
            #self.logger.warn("Received message to unknown framework: %s", framework_id['value'])
            #self.retry_manager.retry(request)
        #return framework, None

    def http_kill(self, framework_id, task_id, agent_id):
        kill_msg = {
            'framework_id' : framework_id,
            'task_id' : task_id
        }
        if agent_id:
            kill_msg['agent_id'] = agent_id

        payload = {
            'mesos.internal.KillTaskMessage' : kill_msg
        }
        request = {
            'source_id' : None, # indicate http type
            'payload_type' : 'json',
            'ext_payload' : None,
            'payload' : payload
            }
        framework, _ = self.kill_task(request)
        if framework:
            self.__release_framework_lock(framework)

    def __kill_task(self, task_id, framework_id, framework, http = False):
        task_name = task_id['value']
        task_dict = framework.get('task_dict', {})
        task = task_dict.get(task_name)
        if task is not None:
            task_dict[task_name]['state'] = 'TASK_KILLED'
            task['end_time'] = time.time()
            self.__add_delete_element(task_dict, task_name)
            status_update = {}
            status_update['framework_id'] = framework_id
            status_update['timestamp'] = time.time()
            status_uuid = self.__generate_uuid()
            status_update['uuid'] = status_uuid # deprecated
            status_update['status'] = {
                'task_id' : task_id,
                'state' : 'TASK_KILLED',
                'uuid' : status_uuid, # new one
#                'source' : 'SOURCE_EXECUTOR_?MASTER'
            }
            channel = framework['channel_name']
            self.logger.trace("task_info=%s" % task_dict[task_name]['task_info'])
            slave_id = task['task_info']['agent_id'] if 'agent_id' in task['task_info'] else task['task_info'].get('slave_id')
            if slave_id:
                status_update['status']['slave_id'] = slave_id
            self.logger.trace("status_update=%s" % status_update)
            self.send_status_update(channel, framework, status_update)
            # Scheduler gets the task update, send shutdown to the executor
            slave_dict = framework.get('slave_dict',{})
            if slave_id:
                slave = slave_dict.get(slave_id['value'])
                if slave:
                    if not slave.get('is_command_executor', False):
                        self.__credit_resources(slave, task['task_info'])
                    if not self.send_kill_task(framework_id, slave, task_id, http):
                        self.retry_manager.retry(request)
                else:
                    self.logger.warn("Shutdown on task [%s] without a slave [%s] in slave dict" % (task_name, slave_id['value']))
            else:
                self.logger.warn("Shutdown on task [%s] without a slave in task dict: task_info=%s" % (task_name, task['task_info']))
            #slave['offerable'] = True
            offer_event = framework.get('offer_event')
            self.logger.debug("Setting empty AsyncResult/Event: %s" % repr(offer_event))
            offer_event.set()
        else:
            self.logger.warn('Request to kill unknown task: %s' % task_id)
            status_update = {}
            status_update['framework_id'] = framework_id
            status_update['timestamp'] = time.time()
            status_uuid = self.__generate_uuid()
            status_update['uuid'] = status_uuid
            status_update['status'] = {
                'task_id' : task_id,
                'state' : 'TASK_KILLED',
                'uuid' : status_uuid
            }
            # Aurora framework complains of illegal state transition LOST->KILLED
            # when status update sent on a kill for the task which is already lost
            # on the other hand Marathon gets stuck if status update is not sent here
            if False:
                self.logger.warn('Not sending status update on request to kill unknown task')
            else:
                self.logger.warn('Sending status update on request to kill unknown task')
                # Scheduler gets the task update, sends shutdown to the executor
                channel = framework['channel_name']
                self.send_status_update(channel, framework, status_update)
                # We are going to retry to see if we can actually kill this task if it comes back
                self.retry_manager.retry(request)

    def kill_task(self, request):
        self.logger.info('Kill task: %s' % request)
        http = False if request.get('source_id') else True
        self.adapter.kill_task(request)
        message = request.get('payload', {}).get('mesos.internal.KillTaskMessage')
        if not message:
            self.logger.warn("Kill task: empty message")
            return None, None
        framework_id = message['framework_id']
        framework = FrameworkTracker.get_instance().get_framework_and_store_request_framework_id(request, framework_id['value'])
        if not framework:
            # Requeue until the framework comes back
            self.retry_manager.retry(request)
            return None, None

        # Acquire framework lock
        self.__acquire_framework_lock(framework)
        self.__kill_task(message['task_id'], framework_id, framework, http)
        return framework, None

    def __process_remaining_offers(self, framework, remaining_offers, filters):
        # Loop through the slaves and let this slave know tremaining_offershat there is nothing to do
        max_rejected_offers = int(framework['config']['max_rejected_offers'])
        offer_event = framework.get('offer_event')
        slave_dict = framework.get('slave_dict',{})
        self.logger.debug('Max rejected offers: %s, Remaining Offers in this request: %s' % (max_rejected_offers,len(remaining_offers)))
        self.logger.debug('filters: %s' % filters)
        self.logger.debug("Checking slaves for offer ids [%s]" % remaining_offers)
        reoffer_time = None
        if len(remaining_offers) == 0:
            # Nothing to do...
            self.logger.debug('No remaining offers, return')
            return
        for offer_id in remaining_offers:
            offer = framework.get('offers',{}).get(offer_id)
            if not offer:
                # We don't have a record of this offer... ignore
                self.logger.warn("Received a launch tasks against an unknown offer id: %s" % offer_id)
                continue

            offer_slave_name = offer['slave_id']['value'] if 'slave_id' in offer else offer['agent_id']['value']
            slave = slave_dict.get(offer_slave_name)
            if not slave:
                if not offer_slave_name.startswith('place-holder'):
                    # We don't have a slave for this offer
                    self.logger.warn("Received a launch tasks against an unknown slave id")
                else:
                    # Honor refuse_seconds parameter
                    if filters and filters.has_key('refuse_seconds'):
                        refuse_seconds = filters.get('refuse_seconds', 0)
                        if refuse_seconds > 0:
                            offerable_after = time.time() + refuse_seconds
                            framework['__placeholder_offerable_after'] = offerable_after
                            self.logger.debug('Refuse seconds is set to: %s for placeholder offer, offerable after: %s' % (refuse_seconds, offerable_after))
                            if not reoffer_time or offerable_after < reoffer_time:
                                reoffer_time = offerable_after
                            continue
                        else:
                            self.logger.debug('Filters do not have refuse_seconds parameter set (in not slave)')
                    self.logger.debug('Adding offer %s for deletion' % offer_id)
                    self.__add_delete_element(framework['offers'], offer_id)
                continue

            # Mark this slave as offerable
            slave['offerable'] = True
            self.logger.debug("Slave [%s] has offer [%s]" %
                              (slave['id']['value'], slave['offer']['id']['value'] if 'offer' in slave else 'None'))

            task_count = slave.get('task_count',0)
            if task_count > 0:
                self.logger.debug("Slave refused offer but has running tasks.   Should tune job class and config.")
                self.__add_delete_element(framework['offers'], offer_id)
                self.logger.debug("Making it not offerable")
                slave['offerable'] = False
                continue
            # Forward this message to our executor runner
            refused_count = slave.get("refused_count",0)
            refused_count += 1
            slave['refused_count'] = refused_count
            self.logger.debug("Slave has refused [%d] offers" % refused_count)
            # Honor refuse_seconds parameter
            if filters and filters.has_key('refuse_seconds'):
                refuse_seconds = filters.get('refuse_seconds', 0)
                if refuse_seconds > 0:
                    offerable_after = time.time() + refuse_seconds
                    slave['offerable_after'] = offerable_after
                    self.logger.debug('Refuse seconds is set to: %s, offerable after: %s' % (refuse_seconds, offerable_after))
                else:
                    self.logger.debug('Filters do not have refuse_seconds parameter set')
                    offerable_after = time.time() + MesosHandler.FRAMEWORK_OFFER_MIN_WAIT_IN_SECONDS
                    slave['offerable_after'] = offerable_after
                    self.__add_delete_element(framework['offers'], offer_id)
            else:
                self.logger.debug('Message has no filters. Setting default refuse value: %s' % MesosHandler.FRAMEWORK_OFFER_MIN_WAIT_IN_SECONDS)
                offerable_after = time.time() + MesosHandler.FRAMEWORK_OFFER_MIN_WAIT_IN_SECONDS
                slave['offerable_after'] = offerable_after
                self.__add_delete_element(framework['offers'], offer_id)

            if not reoffer_time or slave['offerable_after'] < reoffer_time:
                reoffer_time = slave['offerable_after']
            if refused_count > max_rejected_offers:
                self.logger.debug("No executor to shutdown...Shutdown the runner")
                slave_channel = slave['channel']
                self.send_slave_shutdown_message(slave_channel.name)
                self.__delete_slave(framework, slave)
            else:
                # Just hang out... we should get reoffered
                self.logger.debug("We should get reoffered")
                continue

            # CHB: This is dangerous... we could have pending jobs with tasks assigned so they may have work
            # to do.  Don't delete them just because all of the running slaves are done...
            #if len(slave_dict.keys()) == 1:
            #    # No running slaves left... lets delete our job
            #    self.adapter.delete_jobs_delay(framework)
            #    # Need to make a copy since we are modifying the set
            #    for job_id in set(framework.get('job_id',[])):
            #        if job_id is not None:
            #            self.job_monitor.stop_job_monitoring(job_id[0])
            #            framework['job_id'].remove(job_id)

        # Trigger a run of the offer thread...
        if reoffer_time:
            self.logger.debug("Trigger run of the offer thread")
#            if framework.get('http', False):
#                self.__release_framework_lock(framework)
            framework['__next_offer_time'] = reoffer_time + 0.25
            self.logger.debug("Setting empty AsyncResult/Event: %s" % repr(offer_event))
            offer_event.set()

    def http_decline(self, framework_id, offer_ids, filters):
        self.logger.debug("http_decline")
        payload = {
            'mesos.internal.LaunchTasksMessage' : {
                'framework_id' : framework_id,
                'offer_ids' : offer_ids,
                'filters' : filters,
                'tasks' : []
             }
        }
        request = {
            'source_id' : None, # indicate http type
            'payload_type' : 'json',
            'ext_payload' : None,
            'payload' : payload
            }
        framework, _ = self.launch_tasks(request)
        self.logger.debug("http_decline: after launch_tasks")
        if framework:
            self.__release_framework_lock(framework)

    def http_accept_launch(self, framework_id, offer_ids, filters, launch):
        payload = {
            'mesos.internal.LaunchTasksMessage' : {
                'framework_id' : framework_id,
                'offer_ids' : offer_ids,
                'filters' : filters,
                'tasks' : launch['task_infos']
             }
        }
        request = {
            'source_id' : None, # indicate http type
            'payload_type' : 'json',
            'ext_payload' : None,
            'payload' : payload
            }
        framework, _ = self.launch_tasks(request)
        self.logger.debug("http_accept_launch: after launch_tasks")
        if framework:
            self.__release_framework_lock(framework)

    def launch_tasks(self, request):
        self.logger.info('Launch tasks: %s' % request)
        http = not request.get('source_id')
        payload = request.get('payload')
        if not payload:
            self.logger.warn("Launch tasks: empty payload")
            return None, None
        message = payload.get('mesos.internal.LaunchTasksMessage')
        if not message:
            self.logger.warn("Launch tasks: empty message")
            return None, None
        framework_id = message['framework_id']
        self.logger.debug("Launch tasks for framework id: %s" % framework_id['value'])
        framework = FrameworkTracker.get_instance().get_framework_and_store_request_framework_id(request, framework_id['value'])
        self.logger.trace("Launch tasks: framework data=%s" % framework)

        # Acquire framework lock
        self.__acquire_framework_lock(framework)
        
        if not framework:
            # Wait for framework to come back
            self.logger.debug("No active framework for framework id %s, wait for it to come back" % framework_id['value'])
            self.retry_manager.retry(request)
#            if http:
#                self.__release_framework_lock(framework)
            return None, None

        scheduler_channel_name = framework.get('channel_name')
        slave_dict = framework.get('slave_dict',{})
        offer_ids = [ oid['value'] for oid in message.get("offer_ids",[]) ]
        remaining_offer_ids = dict((k,True) for k in offer_ids)
        filters = message.get('filters', {})

        task_dict = framework.get('task_dict', {})
        framework['task_dict'] = task_dict
        tasks = message.get('tasks',[])
        # Keep track of our job-id to placeholder mappings while we work through the tasks
        placeholder_to_jobid = {}
        self.logger.debug('Number of tasks: %s' % len(tasks))
        for t in tasks:
            slave_id = t['slave_id'] if 'slave_id' in t else t['agent_id']
            self.logger.debug("Processing task %s, on slave %s" % (t['task_id']['value'], slave_id['value']))
            # Save task
            task_id = t['task_id']
            task_record = {}
            task_record['task_info'] = t
            task_record['state'] = "TASK_STAGING"
            task_record['queue_time'] = time.time()
            task_record['start_time'] = ""
            task_record['end_time'] = ""
            task_record['lost_time'] = ""
            task_record['offer_ids'] = offer_ids
            self.logger.debug("Setting offer ids to: %s" % task_record['offer_ids'])
            task_dict[task_id['value']] = task_record

            if slave_id['value'].startswith('place-holder'):
                self.logger.debug("Processing placeholder slave: %s" % slave_id['value'])
                # This is a response to our 'query' offer
                framework_config = framework['config']
                existing_job_id = placeholder_to_jobid.get(slave_id['value'])
                if not existing_job_id:
                    # We need to submit our actual runner...
                    concurrent_tasks = int(framework_config.get('concurrent_tasks',1))
                    self.logger.debug("Scaling up for slave: %s" % slave_id['value'])
                    # This is our 'big scale' based on a known need.  Step up in concurrent tasks.
                    job_id = self.scale_up(framework, tasks=[t], scale_count=concurrent_tasks)
                    if len(job_id) > 0:
                        task_record['job_id'] = sorted(job_id)[0][0]
                    else:
                        # We can't start a job for this... probably never should have
                        # offered it. Need to send a lost task
                        self.logger.debug("Could not scale up")
                        self.__process_task_lost_status_update(t, framework, slave_id)
                        continue
                    placeholder_to_jobid[slave_id['value']] = task_record['job_id']
                    framework['concurrent_tasks'] = concurrent_tasks
                else:
                    task_record['job_id'] = existing_job_id

                # Now mark these tasks as lost...
                # Fix up the slave value... it is probably 'place-holder'
                #task['task_info']['slave_id'] = slave['id']
                #tasks.append(task['task_info'])
                # Send a task lost for this task
                send_task_lost = ValueUtility.to_boolean(framework_config.get('send_task_lost', 'True'))
                self.logger.debug('Send task lost: %s' % send_task_lost)
                if send_task_lost:
                    #Scheduler gets the task update, send shutdown to the executor
                    self.__process_task_lost_status_update(t, framework, slave_id)
                continue

            # We have an executor runner up and running
            if slave_id['value'] not in slave_dict:
                self.logger.error("Slave %s is not in slave dictionary" % slave_id['value'])
                continue

            slave = slave_dict[slave_id['value']]
            self.logger.debug('Have already executor runner up and running: slave=%s' % slave)

            # Need to set the job id based on the slave id
            slave_job_id = NamingUtility.get_job_id_from_slave_id(slave["id"]["value"])
            if slave_job_id is None:
                self.logger.error("Cannot extract job id from: %s" % slave["id"]["value"])
#                if http:
#                    self.__release_framework_lock(framework)
                return framework, None
            job_id = slave_job_id

            # Mark this offer as 'used'
            current_offer = slave.get('offer')
            if current_offer and remaining_offer_ids.has_key(current_offer['id']['value']):
                remaining_offer_ids[current_offer['id']['value']] = False
            else:
                if current_offer:
                    self.logger.warn("Slave %s has no offer" % (slave_id['value']))
                else:
                    self.logger.warn("Unable to find offer in slave %s" % slave_id['value'])

            task_record['job_id'] = job_id
            task_name = t['task_id']['value']
            command_executors_cnt = len(slave['command_executors'])
            if slave.get('executor') is None and command_executors_cnt == 0:
                # Forward this message to our executor runner
                message = LaunchTasksMessage(self.channel.name, payload)
                slave_channel = slave['channel']
                self.logger.debug('In launch tasks: No executors: Sending launch tasks message to %s' %
                    slave_channel.name)
                slave_channel.write(message.to_json())

                if t.has_key('executor'):
                    slave['executor'] = t['executor']
                else:
#                    slave['command_executors'] = {} # should alredy be initialized on registering executor runner
                    executor = {}
                    executor['executor'] = self.__build_command_executor(framework_id, t)
                    slave['command_executors'][task_name] = executor
                    slave['command_executors'][task_name]['active'] = True
                    slave['is_command_executor'] = True
            elif command_executors_cnt > 0:
                # Forward this message to our executor runner
                message = LaunchTasksMessage(self.channel.name, payload)
                slave_channel = slave['channel']
                self.logger.debug('In launch tasks: Command executors: Sending launch tasks message to %s' %
                    slave_channel.name)
                slave_channel.write(message.to_json())
                if task_name not in slave['command_executors']:
                    executor = {}
                    executor['executor'] = self.__build_command_executor(framework_id, t)
                    slave['command_executors'][task_name] = executor
                    slave['command_executors'][task_name]['active'] = True
            elif slave.get('executor'):
                # Forward this message to our executor runner
                message = LaunchTasksMessage(self.channel.name, payload)
                slave_channel = slave['channel']
                self.logger.debug('In launch tasks: Custom executor: Sending launch tasks message to %s' %
                    slave_channel.name)
                slave_channel.write(message.to_json())

                # Lets scale up here using the normal scale mechanism
                #self.scale_up(framework)

            self.__debit_resources(slave,t)
            slave['offerable'] = True

            # If executor is registered we can run tasks now.
            if slave.get('is_command_executor', False):
                executor_channel = slave['command_executors'][task_name].get('channel')
            else:
                executor_channel = slave.get('executor_channel')

            if executor_channel is not None:
                framework_info = self.__get_framework_info(framework)
                self.run_task(executor_channel,t,framework_info)
            else:
                self.logger.debug("Do not run task %s, executor channel is not set yet" % task_name)

        # Now we need to handle the slaves specified in the offers that don't have tasks to launch
        self.__process_remaining_offers(framework, [ k for k,v in remaining_offer_ids.items() if v ], filters)
        self.adapter.launch_tasks(self, framework_id, tasks) # dummy method
        self.logger.trace("launch_tasks: end")
        return framework, None
#        if http:
#            self.__release_framework_lock(framework)

    def http_reconcile(self, framework_id, tasks):
        payload = {
            'mesos.internal.ReconcileTasksMessage' : {
                'framework_id' : framework_id,
                'statuses' : tasks
             }
        }
        request = {
            'source_id' : None, # indicate http type
            'payload_type' : 'json',
            'ext_payload' : None,
            'payload' : payload
            }
        framework, _ = self.reconcile_tasks(request)
        if framework:
            self.__release_framework_lock(framework)


    def reconcile_tasks(self, request):
        self.logger.info('Reconcile request: %s' % request)
        message = request.get('payload', {}).get('mesos.internal.ReconcileTasksMessage')
        if not message:
            self.logger.warn("Reconcile: empty message")
            return None, None
        (smart_adapter, adapter_status_update_time) = self.adapter.reconcile_tasks(request)
        source_id = request.get('source_id')
        http = False if source_id else True
        endpoint_id = MessagingUtility.get_endpoint_id(source_id)
        reply_to = request.get('reply_to')
        scheduler_channel_name = MessagingUtility.get_notify_channel_name(
            reply_to=reply_to, endpoint_id=endpoint_id)

        # Return status for all requested tasks
        framework_id = message['framework_id']
        framework = FrameworkTracker.get_instance().get_framework_and_store_request_framework_id(request, framework_id['value'])

        # Acquire framework lock
        self.__acquire_framework_lock(framework)
        
        if not framework:
            # We should make sure we monitor this channel though so we can send disconnects
            # Begin monitoring framework channel
            self.logger.debug("Reconcile: no active framework found for framework id: %s" % framework_id['value'])
            self.channel_monitor.start_channel_monitoring(scheduler_channel_name, framework_id['value'])
            self.retry_manager.retry(request)
            return None, None

        retry_list = []
        # First check if we actually have a task list
        if message.has_key('statuses') and len(message['statuses']) > 0:
            self.logger.debug("Reconcile: explicit for: %s" % message['statuses'])
            # Explicit reconciliation...
            for s in message['statuses']:
                # First lets see if we have a record for this task
                task_id = s['task_id']['value']
                t = framework.get('task_dict',{}).get(task_id,{})
                job_status = t.get('state')
                slave_id = s['slave_id'] if 'slave_id' in s else s.get('agent_id')
                if not slave_id:
                    ti = t.get('task_info',{})
                    slave_id = ti['slave_id'] if 'slave_id' in ti else ti.get('agent_id')
                if slave_id and slave_id['value'].startswith("place-holder"):
                    slave_id_value = framework.get('placeholder_to_slave',{}).get(slave_id['value'])
                    self.logger.debug("Reconcile: slave_id in placeholder: %s" % slave_id_value)
                    if slave_id_value:
                        slave_id['value'] = slave_id_value

#                    slave_id = t.get('task_info',{}).get('slave_id')
                self.logger.debug("Reconcile: task %s: info found: %s, slave_id: %s" % (task_id, t, slave_id))

                # If a task is staging lets print out its details here.... we shouldn't get lots of these
                if job_status == "TASK_STAGING":
                    self.logger.debug("Reconcile STAGING task")
                    # Kinda a catch all... if we have a reconcile on a staging task with a job we don't know about
                    # This will catch it, for dumb adapter or leave staging status or skip update at all
                    if smart_adapter:
                        if adapter_status_update_time > 0:
                            queue_time = t.get('queue_time')
                            if not queue_time:
                                if not slave_id:
                                    self.logger.debug("Reconcile: no queue_time, no slave for STAGING task, not sending status update for task")
                                    continue
                                else:
                                    self.logger.debug("Reconcile: no queue_time for STAGING task, leaving STAGING status for task")
                            if time.time() - queue_time < adapter_status_update_time:
                                if not slave_id:
                                    self.logger.debug("Reconcile: STAGING task: have to wait longer, no slave, not sending status update for task")
                                    continue
                                else:
                                    self.logger.debug("Reconcile: STAGING task: have to wait longer, leaving STAGING status for task")
                            else:
                                self.logger.debug("Reconcile: STAGING task: enough time passed, will determine status")
                                job_status = None
                        else:
                            self.logger.debug("Reconcile: STAGING task: no need to wait, will determine status")
                            job_status = None

                if job_status is None:
                    # We don' have a record...
                    if slave_id:
                        # We do not know about the tasks yet
                        # Lets try and query back end scheduler
                        job_id = NamingUtility.get_job_id_from_slave_id(slave_id['value'])
                        if job_id is not None:
                            try:
                                self.adapter.get_job_status(job_id)
                                job_status = "TASK_RUNNING"
                                self.logger.info("Reconcile: determined task status: %s" % job_status)
                            except UnknownJob, ex:
                                job_status = "TASK_LOST"
                                self.logger.info("Reconcile: cannot get task status for job id '%s' \
                                                 (slave id: %s), set status to %s" % \
                                                 (job_id, slave_id['value'], job_status))
                            except CompletedJob, ex:
                                job_status = "TASK_FINISHED"
                                self.logger.debug("Reconcile: task status is TASK_FINISHED for job id '%s' \
                                                  (slave id: %s), (ex: %s)" % \
                                                  (job_id, slave_id['value'], ex))
                            except Exception, ex:
                                job_status = "TASK_LOST"
                                self.logger.warn("Reconcile: cannot get task status for job id '%s' \
                                                  (slave id: %s), unexpected exception: %s" % \
                                                  (job_id, slave_id['value'], ex))
                        else:
                            job_status = "TASK_LOST"
                            self.logger.error("Reconcile: cannot get job id form slave id: %s, set task status to %s" % \
                                              (slave_id['value'], job_status))

                    else:
                        # ... And we don't have a slave to use to query backend scheduler
                        # if our slave has been up for a while we can assume the task is gone
                        if len(t) == 0:
                            if 'lost_candidate' not in framework:
                                framework['lost_candidate'] = {}
                            if task_id not in framework['lost_candidate']:
#                            self.logger.debug("Reconcile: empty task %s, will retry" % task_id)
                                self.logger.debug("Reconcile: empty task %s, add queue time" % task_id)
                                task_record = {}
                                task_record['queue_time'] = time.time()
                                framework['lost_candidate'][task_id] = task_record
                            # retry_list.append(s)
                                continue
                            else:
                                queue_time = framework['lost_candidate'][task_id]['queue_time']
                        else:
                            queue_time = t.get('queue_time')
                            if not queue_time:
                                self.logger.debug("Reconcile: no queue_time, not sending status update for task")
                                continue
                        if time.time() - queue_time > MesosHandler.SLAVE_GRACE_PERIOD:
                            self.logger.debug("Reconcile: slave grace period exceeded, set status for task %s to TASK_LOST with NotValid slave id" % task_id)
                            task_record = {}
                            # slave_id is None here - set it to NotValid
                            # this may cause failures on scheduler side for some frameworks (as in Spark with non-existed
                            # key exception for "NotValid" setting scheduler driver to DRIVER_ABORTED state)
                            slave_id = { 'value' : 'NotValid' }
                            task_record['task_info'] = {'agent_id' if http else 'slave_id': slave_id}
                            task_record['state'] = "TASK_LOST"
                            task_record['offer_ids'] = None
                            t[task_id] = task_record
                            framework['task_dict'] = t
                            job_status = task_record['state']
                            if task_id in framework.get('lost_candidate',{}):
                                del framework['lost_candidate'][task_id]
                        else:
                            self.logger.debug("Reconcile: slave grace period not exceeded, skip status update for task %s" % task_id)
                            continue

                status_update = {}
                status_update['framework_id'] = framework_id
                status_update['timestamp'] = time.time()
                status_uuid = self.__generate_uuid()
                status_update['uuid'] = status_uuid
                status_update['status'] = {
                    'task_id' : s['task_id'],
                    'state' : job_status,
                    'reason' : 'REASON_RECONCILIATION',
                    'agent_id' if http else 'slave_id' : slave_id,
                    'uuid' : status_uuid
                }

                channel = framework['channel_name']
                self.send_status_update(channel, framework, status_update)

            if len(retry_list) > 0:
                self.logger.debug("Reconcile: will retry to get statuses: %s" % retry_list)
                del message['statuses']
                message['statuses'] = retry_list
                self.retry_manager.retry(request)
        else:
            # Implicit reconciliation... Send all non-completed tasks
            self.logger.debug("Reconcile: implicit")
            self.logger.trace("All tasks: %s" % framework.get('task_dict',{}))
            for t in framework.get('task_dict',{}).values():
                state = t.get('state')
                self.logger.debug("Task %s" % t)
                if state == 'TASK_RUNNING' or state == 'TASK_STAGING':
                    status_update = {}
                    status_update['framework_id'] = framework_id
                    status_update['timestamp'] = time.time()
                    status_uuid = self.__generate_uuid()
                    status_update['uuid'] = status_uuid
                    status_update['status'] = {
                        'task_id' : t['task_info']['task_id'],
                        'state' : state,
                        'reason' : 'REASON_RECONCILIATION',
                        'uuid' : status_uuid
                    }

                    channel = framework['channel_name']
                    self.send_status_update(channel, framework, status_update)
        return framework, None

    def register_executor_runner(self, request):
        self.logger.info('Register executor runner, request: %s' % request)
        payload = request.get('payload')
        if not payload:
            self.logger.warn("Register executor runner: empty payload")
            return None, None

        cf = ChannelFactory.get_instance()

        source_id = request['source_id']
        slave_endpoint_id = MessagingUtility.get_endpoint_id(source_id)

        slave = {}
        slave_id = payload['slave_id']
        slave['id'] = slave_id
        slave['hostname'] = payload['host']
        slave['port'] = payload['port']
        slave_channel_name = MessagingUtility.get_notify_channel_name(
            reply_to=None, endpoint_id=slave_endpoint_id)
        slave_channel = cf.create_channel(slave_channel_name)
        slave['channel'] = slave_channel
        slave['offerable'] = False
        # We should probably have a way to definitively distinguish registration and reregistration
        slave['registered_time'] = time.time()
        slave['executor_reregistered_time'] = ""
        slave['executor_registered_time'] = ""
        slave['command_executors'] = {}

        framework_id = payload['framework_id']
        framework_name = framework_id['value']
        framework = FrameworkTracker.get_instance().get_framework_and_store_request_framework_id(request, framework_name)
        self.logger.trace("Register executor runner: for name %s got framework from tracker: %s" % (framework_name, framework))
        # Acquire framework lock
        self.__acquire_framework_lock(framework)
        
        if framework is None:
            # Job registering for a gone framework... shut it down...
            self.logger.warn("Register executor runner: registration for non-existent framework: %s" % framework_id)
            # First check if this is a framework that we know we have deleted
            #  This could be a  job starting right at framework termination
            if FrameworkTracker.get_instance().is_framework_finished(framework_name):
                # We know that this is a deleted framework... shutdown the slave immediately
                self.logger.debug("Register executor runner: framework %s is deleted" % framework_id)
                self.send_slave_shutdown_message(slave_channel_name)
                return None, None
            retry_count = payload.get('retry_count', 0)
            if retry_count > 0:
                self.logger.debug("Register executor runner: retry count=%d" % retry_count)
                max_retry_count = payload.get('max_retry_count', 0)
                if retry_count < max_retry_count:
                    self.retry_manager.retry(request)
                else:
                    self.send_slave_shutdown_message(slave_channel_name)
            else:
                # Schedule a future delete if the framework doesn't show up
                self.logger.debug("Register executor runner: schedule a future delete if framework %s doesn't show up" % framework_id)
                self.__shutdown_if_no_framework_with_delay(framework_name, slave_channel_name, slave_id['value'])
            return None, None

#        http = framework.get('http', False)
        http = True if framework['channel_name'] == "http" else False

        self.__initialize_slave_resources(framework, slave)
        self.logger.debug('Register executor runner on channel %s, slave info: %s' % (slave_channel_name, slave))

        slave_dict = framework.get('slave_dict', {})
        self.logger.debug("slave_dict before: %s" % slave_dict)
        slave_dict[slave_id['value']] = slave
        framework['slave_dict'] = slave_dict
        self.logger.debug("slave_dict after: %s" % slave_dict)

        # Make sure that this jobid is in our framework
        job_ids = framework.get('job_ids', [])
        framework_config = framework['config']
        #Set job id... this is likely a registration after a failover
        self.logger.debug("Register executor runner: updating job id in framework: %s, job_ids: %s" %
                          (framework_id["value"], job_ids))
        job_id = payload['job_id']
        job_id_tuple = self.adapter.get_job_id_tuple(job_id)
        job_found = False
        for j in job_ids:
            if j[0] == job_id:
                job_found = True
                break
        if not job_found:
            job_ids.append(job_id_tuple)
        self.logger.debug('Register executor runner: job ids after update: %s' % job_ids)
        framework['job_ids'] = job_ids
        # Fix up the concurrent tasks value
        #concurrent_tasks = int(framework_config.get('concurrent_tasks', 1))
        #concurrent_tasks+=1
        #framework['concurrent_tasks'] = concurrent_tasks
        self.job_monitor.start_job_monitoring(job_id, framework_name)

        # Begin monitoring slave channel
        self.channel_monitor.start_channel_monitoring(slave_channel_name,
            framework_name, slave_id['value'])

        # If tasks are present we need to add these back to our list
        tasks = payload.get('tasks',[])
        if len(tasks) > 0:
            # Tasks are already running... can't launch new ones yet
            if slave.get('is_command_executor', False):
                for t in tasks:
                    task_name = t['task_id']['value']
                    slave['command_executors'][task_name]['executor'] = t.get('executor')
                    self.logger.debug("Register executor runner: set slave command executor to: %s" % t.get('executor'))
            else:
                slave['executor'] = tasks[0].get('executor')
                self.logger.debug("Register executor runner: set custom slave executor to: %s" % slave['executor'])
#            return
            for t in payload.get('tasks',[]):
                # lets try and rebuild the state...
#                slave['executor'] = t.get('executor')
                task_dict = framework.get('task_dict', {})
                task_record = {}
                task_record['task_info'] = t
                task_record['state'] = "TASK_RUNNING"
                task_record['offer_ids'] = None
                task_record['job_id'] =  payload['job_id']
                task_dict[t['task_id']['value']] = task_record
                framework['task_dict'] = task_dict
                # We need to deduct the slave resources since we have a running task
                self.__debit_resources(slave,task_record['task_info'])
#            self.adapter.register_executor_runner(self, framework_id, slave_id)
            return framework, None

        executor_in_docker = False
        task_in_docker = False
        # We should have some tasks waiting for us....
        # Forward this message to our executor runner
        self.logger.debug("Register executor runner: looking for tasks with job_id: %s" % payload['job_id'])
        for task_id, task in framework.get('task_dict', {}).items():
            # Look for non-running unassociated tasks
            if task['state'] == 'TASK_STAGING':
                self.logger.debug("Register executor runner: founding pending task: %s" % task_id)
                if not task.has_key('job_id'):
                    self.logger.debug("Register executor runner: task does not have job id. Skipping... :%s" % task)
                    continue
                self.logger.debug("Register executor runner: found task %s with job id %s" % (task_id, task['job_id']))
                if task['job_id'] == payload['job_id']:
                    task_slave_id = task['task_info']['slave_id'] if 'slave_id' in task['task_info'] else task['task_info']['agent_id']
                    if task_slave_id['value'].startswith('place-holder'):
                        # We need to record the mapping of this slave to place-holder
                        placeholder_to_slave = framework.get('placeholder_to_slave',{})
                        placeholder_to_slave[task_slave_id['value']] = slave['id']['value']
                        framework['placeholder_to_slave'] = placeholder_to_slave
                        slave['placeholder'] = task_slave_id['value']
                        # Fix up the slave value... it is probably 'place-holder'
                        task_slave_id = slave['id']
                        # Also set the command executor info if necessary
                        if task['task_info'].has_key('executor'):
                            slave['executor'] = task['task_info']['executor']
                            # check for docker
                            executor_container = slave['executor'].get('container')
                            if executor_container is not None:
                                if executor_container['type'] == 'DOCKER':
                                    executor_in_docker = True
                        else:
                            executor = {}
                            executor['executor'] = self.__build_command_executor(framework_id, task['task_info'])
                            slave['command_executors'][task_id] = executor
                            slave['command_executors'][task_id]['active'] = True
                            slave['is_command_executor'] = True
                        tasks.append(task['task_info'])
                        # check for docker
                        task_container = task['task_info'].get('container')
                        if task_container is not None:
                            if task_container['type'] == 'DOCKER':
                                tsid = task_slave_id['value']
                                sid = slave["id"]["value"]
                                self.logger.debug("tsid=%s, sid=%s" % (tsid, sid))
                                if tsid == sid:
                                    task_in_docker = True
                    # Deduct resources since we have allocated tasks to this slave
                    self.logger.debug("Register executor runner: append task %s with job id %s" % (task_id, task['job_id']))
                    self.__debit_resources(slave,task['task_info'])
                else:
                    self.logger.debug("Register executor runner: skip task %s with job id %s" % (task_id, task['job_id']))
            else:
                self.logger.debug("Register executor runner: skip task %s: not TASK_STAGING: %s" % (task_id, task['state']))

        if len(tasks) > 0:
            # OK...tasks waiting for us means we are already committed... disable offers on
            # this host until a task completes...
            payload =  self.__build_launch_tasks_payload(framework_id, tasks, http)

            message = LaunchTasksMessage(self.channel.name, payload)
            self.logger.debug('Register executor runner: sending launch tasks message to %s: %s' %
                               (slave_channel.name, tasks))
            slave_channel.write(message.to_json())
            # We won't have executor info yet if this is a command executor
#            self.logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!")
#            if tasks[0].has_key('executor'):
#                slave['executor'] = tasks[0]['executor']
#            else:
#            if slave.get('is_command_executor', False):
#                for t in tasks:

            # Lets scale up here if not in docker
            if executor_in_docker or task_in_docker:
                self.logger.debug("Do not scale up in docker")
            else:
                self.scale_up(framework)
        
        # Enable our offerability
        slave_dict[slave_id['value']]['offerable'] = True
        #self.offer_event.set()

        self.adapter.register_executor_runner(self, framework_id, slave_id)
        return framework, None

    def reregister_executor(self, request):
        """ Reregistering a lost executor """
        message = request.get('payload', {}).get('mesos.internal.ReregisterExecutorMessage')
        if not message:
            self.logger.warn("Reregister Executor: empty message")
            return None, None
        self.logger.info("Reregister Executor: %s from: %s" % (message, request['reply_to']))
        framework_id = message["framework_id"]
        framework = FrameworkTracker.get_instance().get_framework_and_store_request_framework_id(request, framework_id['value'])
        if framework is None:
            self.logger.info("No framework (%s) for executor. Waiting for framework reregister." % framework_id['value'])
            #self.retry_manager.retry(request)
            return None, None

        # Acquire framework lock
        self.__acquire_framework_lock(framework)
        
        # In our message we should have the reply_to field set to the channel name of our
        # executor runner...
        for slave in framework.get('slave_dict',{}).values():
            if slave['channel'].name == request['reply_to']:
                # This is our slave!
                break
        else:
            self.logger.info("Unknown slave for framework %s" % framework_id)
            return framework, None

#        executor_info = slave.get('executor')
        framework_info = self.__get_framework_info(framework)
        slave_id = slave["id"]
        slave_info = {}
        slave_info["hostname"] = slave["hostname"]
        slave_info["port"] = slave["port"]
        slave_info["id"] = slave["id"]

        # Save this executor channel in the slave
        executor_endpoint_id = MessagingUtility.get_endpoint_id(request['source_id'])
        executor_channel_name = MessagingUtility.get_notify_channel_name(
            reply_to=None, endpoint_id=executor_endpoint_id)
        cf = ChannelFactory.get_instance()
        executor_channel = cf.create_channel(executor_channel_name)
        slave['executor_channel'] = executor_channel

        slave_job_id = NamingUtility.get_job_id_from_slave_id(slave["id"]["value"])
        if slave_job_id is None:
            self.logger.error("Cannot reregister executor: incorrect slave job id: %s" % slave["id"]["value"])
            return framework, None
        job_id = slave_job_id

        # Check to see if we have uncompleted tasks...
        for t in message.get('tasks',[]):
            # lets try and rebuild the state...
            task_name = t['task_id']['value']
            if t.has_key('executor'):
                slave['executor'] = t['executor']
                self.logger.debug("Task %s used custom executor" % task_name)
            else:
                self.logger.debug("Task %s used command executor, rebuilding it" % task_name)
                executor = {}
                executor['executor'] = self.__build_command_executor(framework_id, t)
                executor['channel'] = executor_channel
                slave['command_executors'][task_name] = executor
                slave['command_executors'][task_name]['active'] = True
                slave['is_command_executor'] = True
            task_dict = framework.get('task_dict', {})
            task_record = {}
            task_record['task_info'] = t
            task_record['state'] = "TASK_RUNNING"
            task_record['offer_ids'] = None
            task_record['job_id'] = job_id
            task_dict[task_name] = task_record
            framework['task_dict'] = task_dict
            # So we need to debit for these
            self.__debit_resources(slave,t)

        # Reinitialize the resource count... we will calculate whats running and debit
        #self.__initialize_slave_resources(framework, slave)
        # We are revesing the list and using negative timestamps so we can use native
        # string sorting on RUNNING vs FINISHED (processing running first)
        for u in sorted(message.get('updates',[]),key=lambda i: (int(i['status']['timestamp'])*-1,i['status']['state']),reverse=True):
            self.logger.debug('Processing task update for task: %s' % u)
            self.handle_status_update(framework, u)

        # Now send our response
        executor_reregistered = {
          'slave_id' : slave_id,
          'slave_info' : slave_info,
        }
        response_payload = executor_reregistered
        message = ExecutorReregisteredMessage(self.channel.name, response_payload)

        cf = ChannelFactory.get_instance()
        self.logger.debug('Sending executor reregistered message via channel %s: %s' % (executor_channel.name, message))
        executor_channel.write(message.to_json())
        slave['executor_reregistered_time'] = time.time()

        # TODO: Fix this...CPP is sending a reply_to now when it shouldn't
        # UGGH.. we are still using the reply_to to make an association between
        # the executor_runner and the executor... has to stay for now.
        del request["reply_to"]

        # Finally mark ourselves as offerable again. Our available resources should be correct
        slave['offerable'] = True
        return framework, None

    def register_executor(self, request):
        self.logger.debug("register_executor request=%s" % request)
        http = False if request['source_id'] else True
        """ Just track this and send it on to our executor runner """
        message = request.get('payload', {}).get('mesos.internal.RegisterExecutorMessage')
        if not message:
            self.logger.warn("Register Executor: empty message")
            return None, None
        self.logger.info("Register Executor: %s from: %s" % (message, request['reply_to']))
        executor_id_val = message["executor_id"]["value"]
        framework_id = message["framework_id"]
        framework = FrameworkTracker.get_instance().get_framework_and_store_request_framework_id(request, framework_id['value'])
        if framework is None:
            self.logger.info("No framework (%s) for executor. Waiting for framework register." % framework_id)
            return None, None

        # Acquire framework lock
        self.__acquire_framework_lock(framework)
        
        # In our message we should have the reply_to field set to the channel name of our
        # executor runner...
        for slave in framework['slave_dict'].values():
            self.logger.debug("Iterating slave: %s" % slave)
            if http:
                if slave.get('executor',{}).get('executor_id',{}).get('value') == executor_id_val:
                    break
            else:
                if slave['channel'].name == request['reply_to']:
                    # This is our slave!
                    break
        else:
            err_msg = 'Unknown slave for framework %s, push to retry manager' % framework_id
            self.logger.info(err_msg)
            self.retry_manager.retry(request)
            return None, None

        self.logger.debug("Our slave: %s" % slave)
        is_command_executor = slave.get('is_command_executor', False)
        if is_command_executor:
            executor_slave = slave['command_executors'].get(executor_id_val)
            if executor_slave:
                executor_info = executor_slave.get('executor')
            else:
                self.logger.error("Cannot find command executor info in slave %s for task %s, push to retry manager" %
                                  (slave['channel'].name, executor_id_val))
                self.logger.debug("Slave: %s" % slave)
                self.retry_manager.retry(request)
                return None, None
        else:
            executor_info = slave.get('executor')

        framework_info = self.__get_framework_info(framework)
        slave_id = slave["id"]
        slave_info = {
            'hostname' : slave['hostname'],
            'port' : slave['port'],
            'id' : slave['id']
        }

        if not http:
            # Save this executor channel in the slave
            executor_endpoint_id = MessagingUtility.get_endpoint_id(request['source_id'])
            executor_channel_name = MessagingUtility.get_notify_channel_name(
                reply_to=None, endpoint_id=executor_endpoint_id)
            cf = ChannelFactory.get_instance()
            executor_channel = cf.create_channel(executor_channel_name)
            slave['executor_channel'] = executor_channel

            self.executor_registered(executor_channel, executor_info, framework_id,
                                    framework_info, slave_id, slave_info)
        else:
            subscribed = {
                'executor_info' : executor_info,
                'framework_info' : framework_info,
                'agent_info' : slave_info
            }

        slave['executor_registered_time'] = time.time()

        # TODO: Fix this...CPP is sending a reply_to now when it shouldn't
        # UGGH.. we are still using the reply_to to make an association between
        # the executor_runner and the executor... has to stay for now.
        del request["reply_to"]

        # Now we get to run some tasks...
        slave_job_id = NamingUtility.get_job_id_from_slave_id(slave_id['value'])
        self.logger.debug("Register Executor: slave_job_id=%s " % slave_job_id)
        launch = []
        for t in framework.get('task_dict').values():
            if slave_job_id is None:
                self.logger.error("Cannot register executor: incorrect job id: %s" % slave['id']['value'])
                continue
            jid = t.get('job_id', '0')
            if t['state'] == 'TASK_STAGING' and jid == slave_job_id:
                task_name = t['task_info']['task_id']['value']
                cet = is_command_executor and executor_id_val == task_name
                if cet:
                    self.logger.debug("Set channel %s with name %s for command executor for task: %s" %
                                      (executor_channel, executor_channel.name, task_name))
                    slave['command_executors'][task_name]['channel'] = executor_channel
                # in case of command executor run only task associated with executor (executor id is created as task id)
                # for custom executor always run all tasks
                if not is_command_executor or cet:
                    self.logger.debug("Run task: %s" % t)
                    if http:
                        launch.append(t['task_info'])
                    else:
                        self.run_task(executor_channel, t['task_info'], framework_info)
                else:
                    self.logger.debug("Skip command executor task: %s" % t)
            else:
                self.logger.debug("Skip task due to different job id or not staging status: %s, slave_job_id=%s, jid=%s" %
                                  (t, slave_job_id, jid))

        # look for docker signature in executor info or task info, do not scale up if found
        executor_in_docker = False
        if 'executor' in slave and slave['executor'] is not None:
            executor_container = slave['executor'].get('container')
            if executor_container is not None:
                if executor_container['type'] == 'DOCKER':
                    executor_in_docker = True

        task_in_docker = False
        for task in framework['task_dict'].values():
            task_info = task['task_info']
            task_container = task_info.get('container')
            if task_container is not None:
                if task_container['type'] == 'DOCKER':
                    tsid = task_info['slave_id']['value']
                    sid = slave["id"]["value"]
#                    self.logger.debug("tsid=%s, sid=%s" % (tsid, sid))
                    if tsid == sid:
                        task_in_docker = True

        if executor_in_docker == False and task_in_docker == False and is_command_executor == False:
            # Finally...scale up whenever we start a new executor
            # CHB - Scale by the normal increment
            # probably do not need scale up here at all
            self.scale_up(framework)
        else:
            #framework['__placeholder_offerable_after'] = 0 # something can be done here to accelerate offers generation?
            self.logger.debug("Do not scale up since registered executor is runnig in docker or command executor")

        if http:
            return subscribed, launch
        else:
            return None, None

    def register_framework(self, request):
        self.logger.info('Register framework: %s' % request)
        message = request.get('payload', {}).get('mesos.internal.RegisterFrameworkMessage')
        if not message:
            self.logger.warn("Register framework: empty message")
            return None, None
        self.logger.trace("message: %s" % message)
        response = FrameworkRegisteredMessage(self.channel.name, {})
        framework = self.process_registration(request, None, message, response)

        # Acquire framework lock
        self.logger.debug("Register framework: acquiring framework lock for framework: %s" % framework.get('id'))
        self.__acquire_framework_lock(framework)

        framework['registered_time'] = time.time()
        framework['reregistered_time'] = ""

        self.logger.debug('Registered framework: %s' % framework)
        return framework, None
        
    def reregister_framework(self, request):
        self.logger.info('Reregister framework: %s' % request)
        message = request.get('payload', {}).get('mesos.internal.ReregisterFrameworkMessage')
        if not message:
            self.logger.warn("Reregister framework: empty message")
            return None, None
        self.adapter.reregister_framework(request)
        self.logger.trace("message: %s" % message)
        framework_id = message['framework']['id']

        response = FrameworkReregisteredMessage(self.channel.name, {})
        framework = self.process_registration(request, framework_id, message, response)
        # Acquire framework lock
        self.logger.debug("Reregister framework: acquiring framework lock for framework: %s" % framework.get('id'))
        self.__acquire_framework_lock(framework)

        framework['reregistered_time'] = time.time()

        self.logger.debug('Reregistered framework: %s' % framework)
        return framework, None

    def http_subscribe(self, framework_info):
        self.logger.info('Subscribe: %s' % framework_info)
        response = {}
        internal = "mesos.internal.ReregisterFrameworkMessage" if framework_info.get('id') else "mesos.internal.RegisterFrameworkMessage"
            
        payload = {
                    internal : {
                       'framework' : framework_info
                    }
                  }
        request = {
            'source_id' : None, # indicate http type
            'reply_to' : 'http',
            'message_id' : str(uuid.uuid1()),
            'payload' : payload
            }
        framework = self.process_registration(request, None, payload[internal], response)
        self.logger.trace("Subscribe response: %s" % response)
        # Acquire framework lock
#        self.logger.debug("Subscribe framework: acquiring framework lock for framework: %s" % framework.get('id'))
#        self.__acquire_framework_lock(framework)

        framework['registered_time'] = time.time()
        framework['reregistered_time'] = ""

        self.logger.debug('Subscribed framework: %s' % framework)
        return response

    # This method handles registration and reregistration
    def process_registration(self, request, framework_id, message, response):
        self.logger.debug("process_registration, request=%s" % request)
        source_id = request.get('source_id')
        http = False if source_id else True
        endpoint_id = MessagingUtility.get_endpoint_id(source_id)
        if framework_id is None:
            framework_id = {}
            framework_id['value'] = 'framework-' + endpoint_id;
            self.logger.debug("Framework registration: generated new framework id %s" % framework_id['value'])
        else:
            self.logger.debug("Framework registration: using existing framework id %s" % framework_id['value'])

        reply_to = request.get('reply_to')
        scheduler_channel_name = MessagingUtility.get_notify_channel_name(
            reply_to=reply_to, endpoint_id=endpoint_id)
        framework = message['framework']
        ext_data = request.get('ext_payload',{})

        # Form response payload
        if http:
            port = self.scheduler_http_port
            host = self.service_hostname
        else:
            cf = ChannelFactory.get_instance()
            port = cf.get_message_broker_connection_port()
            host = cf.get_message_broker_connection_host()

        ip_addr = socket.gethostbyname(host)
        int_addr = struct.unpack('!I', socket.inet_aton(ip_addr))[0]
#        ip_addr = "127.0.0.1"
        ip_addr = "10.0.2.15"
        int_addr = struct.unpack('I', socket.inet_aton(ip_addr))[0]

        master_info = {}
        master_info['id'] = 'master-' + host
        master_info['ip'] = int_addr
        master_info['port'] = int(port)
        master_info['hostname'] = host
        master_info['version'] = MesosHandler.MESOS_VERSION
        master_info['address'] = { 'ip' : ip_addr,
                                   'hostname' : host,
                                   'port' : int(port)
                                 }

        response['payload'] = {
            'framework_id' : framework_id,
            'master_info' : master_info
        }

        # Keep framework info
        resolved_framework = FrameworkTracker.get_instance().get(framework_id["value"])
        if resolved_framework is None:
            self.logger.debug("Framework registration: no existing framework found in tracker")
            resolved_framework = framework
            resolved_framework['init_time'] = time.time()
            # Save the ext data if we have any...
            resolved_framework['ext_data'] = {}
        else:
            self.logger.debug("Framework registration: Existing framework found in tracker: %s" % resolved_framework)

        # Should have already been initialized
        if ext_data is not None:
            resolved_framework['ext_data'].update(ext_data)
        self.logger.debug('Received framework ext_data: %s' % ext_data)
        resolved_framework['endpoint_id'] = endpoint_id
        resolved_framework['id'] = framework_id
        resolved_framework['channel_name'] = scheduler_channel_name
        resolved_framework['master_info'] = master_info
        if http:
            resolved_framework['http'] = True
        self.configure_framework(resolved_framework)

        self.logger.debug("Framework registration: adding to tracker")
        FrameworkTracker.get_instance().add(framework_id['value'], resolved_framework)
        self.logger.debug("Framework registration: storing request framework id in tracker")
        FrameworkTracker.get_instance().store_request_framework_id(request, framework_id['value'])

        # For non http framework
        if not http:
            # Begin monitoring framework channel
            self.channel_monitor.start_channel_monitoring(scheduler_channel_name, framework_id['value'])
        else:
            self.logger.debug("Do not start channgel monitoring to http framework")

        # Start offer greenlet
        if resolved_framework.get('offer_event') is None:
            self.logger.debug("No offer_event, creating new one")
#            resolved_framework['offer_event'] = gevent.event.Event()
#            resolved_framework['offer_event'] = gevent.event.AsyncResult()
            if not http:
                resolved_framework['offer_event'] = gevent.event.Event()
                self.logger.debug("Starting generate offers greenlet")
                gevent.Greenlet.spawn(self.__generate_offers, framework_id)
            else:
                resolved_framework['offer_event'] = gevent.event.AsyncResult()
                self.logger.debug("Do not start generate offers greenlet for http framework")
        else:
            self.logger.debug("Do not start new offer loop due to existing offer event: %s" % resolved_framework['offer_event'])

        # Send response for non http
        if not http:
            scheduler_channel = cf.create_channel(scheduler_channel_name)
            scheduler_channel.write(response.to_json())
            self.logger.debug('Framework registration: wrote response via channel %s: %s' % (scheduler_channel_name, response))

        return resolved_framework

    def register_slave(self, request):
        self.logger.info('Register slave: %s' % request)
        self.adapter.register_slave(request)
        return None, None

    def reregister_slave(self, request):
        self.logger.info('Reregister slave: %s' % request)
        self.adapter.reregister_slave(request)
        return None, None

    def resource_request(self, request):
        self.logger.info('Resource request: %s' % request)
        self.adapter.resource_request(request)
        return None, None

    def http_revive(framework_id, revive):
        payload = {
            'mesos.internal.ReviveOffersMessage' : {
                'framework_id' : framework_id,
             }
        }
        request = {
            'source_id' : None, # indicate http type
            'payload_type' : 'json',
            'ext_payload' : None,
            'payload' : payload
            }
        framework, _ = self.revive_offers(request)
        if framework:
            self.__release_framework_lock(framework)

    def revive_offers(self, request):
        self.logger.info('Revive offers: %s' % request)
        message = request.get('payload', {}).get('mesos.internal.ReviveOffersMessage')
        if not message:
            self.logger.warn("Revive offers: empty message")
            return None, None
        self.adapter.revive_offers(request)
        framework_id = message['framework_id']['value']

        framework = FrameworkTracker.get_instance().get_framework_and_store_request_framework_id(request, framework_id)

        # Acquire framework lock
        self.__acquire_framework_lock(framework)

        if framework:
            # Reset the offerable status on all slaves
            for slave_id, slave in framework.get('slave_dict',{}).items():
                slave['offerable'] = True
                slave['offerable_after'] = 0
            # Reset the placeholder offerable timer
            framework['__placeholder_offerable_after'] = 0

            offer_event = framework.get('offer_event')
            self.logger.debug("Setting empty AsyncResult/Event: %s" % repr(offer_event))
            offer_event.set()

        return framework, None

    def submit_scheduler_request(self, request):
        self.logger.info('Submit scheduler request: %s' % request)
        self.adapter.submit_scheduler_request(request)
        return None, None

    def http_acknowledge(self, framework_id, agent_id, task_id, uuid):
        if not uuid:
            self.logger.debug("http_acknowledge: no uuid, no need to acknowledge")
            return
        payload = {
            'mesos.internal.StatusUpdateAcknowledgementMessage' : {
                'framework_id' : framework_id,
                'agent_id' : agent_id,
                'task_id' : task_id,
                'uuid' : uuid
             }
        }
        request = {
            'source_id' : None, # indicate http type
            'payload_type' : 'json',
            'ext_payload' : None,
            'payload' : payload
            }
        framework, _ = self.status_update_acknowledgement(request)
        if framework:
            self.__release_framework_lock(framework)

    def status_update_acknowledgement(self, request):
        self.logger.info('Status update acknowledgement: %s' % request)
        http = False if request.get('source_id') else True
        # This message justs get sent along
        self.adapter.status_update_acknowledgement(request)

        message = request.get('payload', {}).get('mesos.internal.StatusUpdateAcknowledgementMessage')
        if not message:
            self.logger.warn("Status update acknowledgement: empty message")
            return None, None
        framework_id = message['framework_id']
        slave_id = message['agent_id'] if'agent_id' in message else message.get('slave_id')

        framework = FrameworkTracker.get_instance().get_framework_and_store_request_framework_id(request, framework_id['value'])

        # Acquire framework lock
        self.__acquire_framework_lock(framework)

        # Some frameworks (Marathon, Jenkins) do not set an appropriate slave id...
        if framework:
            self.logger.debug("Current framework: %s" % framework)
            if slave_id:
                slave_id_value = slave_id['value']
                if slave_id_value.startswith("place-holder"):
                    slave_id_value = framework.get('placeholder_to_slave',{}).get(slave_id_value)
                slave = framework.get('slave_dict',{}).get(slave_id_value)
                if slave:
                    if http:
                        ack_event = {
                            'type' : 'ACKNOWLEDGED',
                            'acknowledged' : {
                                'task_id' : message['task_id'],
                                'uuid' : message['uuid']
                            }
                        }
                        self.logger.debug("HTTP: acknowledgement to executor, before set event")
                        slave['async_result'].set(ack_event)
                    else:
                        executor_channel = None
                        if slave.get('is_command_executor', False):
                            task_name = message['task_id']['value']
                            if task_name in slave['command_executors']:
                                executor_channel = slave['command_executors'][task_name].get('channel')
                            else:
                                self.logger.error('Command executor not found for task %s' % task_name)
                        else:
                            executor_channel = slave.get('executor_channel')
                        # Forward the ack to the executor
                        if executor_channel:
                            m = StatusUpdateAcknowledgementMessage(self.channel.name, message)
                            self.logger.debug('Sending status acknowledgement message via channel %s: %s' %
                                            (executor_channel.name, m))
                            executor_channel.write(m.to_json())
                        else:
                            self.logger.warn('Not sending status acknowledgement message: no channel')
                else:
                    self.logger.warn("Not sending status acknowledgement message: no slave for slave id: %s" % slave_id_value)
            else:
                self.logger.warn('Not sending status acknowledgement message: no slave id')
        else:
            self.logger.warn('Not sending status acknowledgement message: no framework')
        self.logger.trace('Status update acknowledgement: end')
        return framework, None
                
    def status_update(self, request):
        self.logger.info('Status update: %s' % request)
        message = request.get('payload', {}).get('mesos.internal.StatusUpdateMessage')
        if not message:
            self.logger.warn("Status update: empty message")
            return None, None
        update = message['update']

        framework = FrameworkTracker.get_instance().get_framework_and_store_request_framework_id(request, 
            update['framework_id']['value'])

        # Acquire framework lock
        self.__acquire_framework_lock(framework)
        
        if self.handle_status_update(framework, update):
            self.retry_manager.retry(request)
        return framework, None

    def handle_status_update(self, framework, update):
        task_id = update['status']['task_id']
        if not framework:
            self.logger.warn('Unable to update status for task: %s from unknown framework: %s'
                % (task_id, update['framework_id']['value']))
            # We should retry
            return True

#        self.send_status_update(framework.get('channel_name'), framework, update)

        # Record the the state in our task dict
        state = update['status']['state']
        self.logger.debug('Handling status update for task %s, framework %s, status=%s' % \
                          (task_id['value'], update['framework_id']['value'], state))
        task_dict = framework.get('task_dict', {})
        task = task_dict.get(task_id['value'])
        if task is not None:
            task['state'] = state
            if state == 'TASK_RUNNING':
                if task.get('start_time') is None or len(str(task.get('start_time'))) == 0:
                    task['start_time'] = time.time()
            # If this slave has finished we can send another offer...
            slave_id_nm = None
            slave_id = None
            if 'slave_id' in update:
                slave_id_nm = 'slave_id'
                slave_id = update['slave_id']
            elif 'agent_id' in update:
                slave_id_nm = 'agent_id'
                slave_id = update['agent_id']
            elif 'slave_id' in task['task_info']:
                slave_id_nm = 'slave_id'
                slave_id = task['task_info']['slave_id']
            elif 'agent_id' in task['task_info']:
                slave_id_nm = 'agent_id'
                slave_id = task['task_info']['agent_id']
#            slave_id = update['slave_id'] if 'slave_id' in update else update.get('agent_id')
#            if not slave_id:
#                slave_id = task['task_info']['slave_id'] if 'slave_id' in task['task_info'] else task['task_info'].get('agent_id')
            if slave_id_nm:
                # enrich update with agent_id information and sent to framework
                update['status'][slave_id_nm] = slave_id
                self.send_status_update(framework.get('channel_name'), framework, update)
                slave = framework['slave_dict'].get(slave_id['value'])
                if slave and (state == "TASK_FINISHED" or state == 'TASK_FAILED'):
                    if not slave.get('is_command_executor', False):
                        self.__credit_resources(slave, task['task_info'])
                        #slave['offerable'] = True #ST consider to uncomment
                        offer_event = framework.get('offer_event')
                        self.logger.debug("Setting empty AsyncResult/Event: %s" % repr(offer_event))
                        offer_event.set()
                    else:
                        # Delete slave if no more running tasks
                        executor_channel = slave['command_executors'][task_id['value']]['channel']
                        self.logger.debug("Deleting command executor with channel %s due to finished task: %s" %
                                        (executor_channel.name, task_id['value']))
                        self.__delete_channel_with_delay(executor_channel.name)
                        slave['command_executors'][task_id['value']]['active'] = False
                        delete_slave = True
                        for val in slave['command_executors'].values():
                            if val['active']:
                                delete_slave = False
                                break
                        if delete_slave:
                            self.logger.debug("All command executors done, delete salve %s" % slave['id']['value'])
                            self.update_completed_executor_summary_db(slave)
                            self.__add_delete_element(framework['slave_dict'], slave['id']['value'])
                            slave_channel = slave['channel']
                            self.__delete_channel_with_delay(slave_channel.name)
                    task['end_time'] = time.time()
                    self.logger.debug("Adding task %s for deletion from dictionary" % task_id['value'])
                    self.__add_delete_element(task_dict, task_id['value'])
            else:
                # just redirect status update to framework
                self.send_status_update(framework.get('channel_name'), framework, update)
                self.logger.warn("No slave id information in both update: %s and task_info of task_dict: %s" %
                                 (update, task['task_info']))
                return True
        else:
            # just redirect status update to framework
            self.send_status_update(framework.get('channel_name'), framework, update)
            self.logger.warn('Unable to update status on unknown task: %s' % task_id['value'])
            #self.logger.trace("task_dict=%s" % task_dict)
            # We should retry
            return True
        return False

    def http_teardown(self, framework_id):
        payload = {
            'mesos.internal.UnregisterFrameworkMessage' : {
                'framework_id' : framework_id,
             }
        }
        request = {
            'source_id' : None, # indicate http type
            'payload_type' : 'json',
            'ext_payload' : None,
            'payload' : payload
            }
        framework, _ = self.unregister_framework(request)
        if framework:
            self.__release_framework_lock(framework)

    def unregister_framework(self, request):
        self.logger.info('Unregister framework: %s' % request)
        message = request.get('payload', {}).get('mesos.internal.UnregisterFrameworkMessage')
        if not message:
            self.logger.warn("Unregister framework: empty message")
            return None, None
        # Send shutdown message and then delete...
        framework_id = message['framework_id']
        framework = self.__delete_framework(framework_id['value'])

        # No need to acquire lock here, framework will be gone from tracker
        
        if framework:
            framework['unregistered_time'] = framework['delete_time']
            return framework, None
        else:
            return None, None

    def unregister_slave(self, request):
        self.logger.info('Unregister slave: %s' % request)
        self.adapter.unregister_slave(request)
        return None, None

###########################

    def __build_command_executor(self, framework_id, task):
#        cm = ConfigManager.get_instance()
        # Need to build up a command executor
        command_executor =  {}
        command_executor['executor_id'] = task['task_id']
        command_executor['framework_id'] = framework_id
        command_executor['name'] = "(Task " + task['task_id']['value'] + ") "
        # deprecated in 1.0.0
        command_executor['source'] = task['task_id']['value']
        # use labels instead
        #command_executor['labels'] = [{'source' : task['task_id']['value']}] # causes json parsing error in cpp
        # If it doesn't have an custom executor it has a command
        command_executor['command'] = task.get('command')
        self.logger.debug("Building command executor info for task: %s" % task['task_id']['value'])
        return command_executor

    def __generate_uuid(self):
        u = uuid.uuid1()
        return base64.b64encode(u.bytes)

    def __delete_channel_with_delay(self, channel_id):
        if channel_id is not None:
            # Delay removing channel to give receiving end chance to cleanup
            gevent.spawn(self.__delete_channel, channel_id)

    def __shutdown_if_no_framework_with_delay(self,framework_id_value,channel_id,slave_id_value):
        gevent.spawn(self.__shutdown_if_no_framework, framework_id_value,channel_id, slave_id_value)

    def __shutdown_if_no_framework(self,framework_id_value,channel_id,slave_id_value):
        self.__scheduled_shutdowns[slave_id_value] = framework_id_value
        self.logger.debug('Shutdown if no framework: %s, slave=%s with delay' %
                          (framework_id_value, slave_id_value))
        gevent.sleep(MesosHandler.MISSING_FRAMEWORK_WAIT_PERIOD_IN_SECONDS)
        framework = FrameworkTracker.get_instance().get(framework_id_value)
        if not framework:
            self.logger.debug('Shutdown if no framework: %s, about to shutdown channel: %s' %
                              (framework_id_value, channel_id))
            self.send_slave_shutdown_message(channel_id)
            # if framework terminated without sending unregister message it is left in active status in db
            # here we can mark it finally as inactive
            if self.framework_db_interface is not None and self.framework_db_interface.is_active():
                self.framework_db_interface.set_framework_summary_status_inactive(framework_id_value)
            if self.__scheduled_shutdowns.get(slave_id_value):
                # Also delete the job...
                job_id = NamingUtility.get_job_id_from_slave_id(slave_id_value)
                if job_id is None:
                    self.logger.error("Cannot delete job: incorrect job id: %s" % slave_id_value)
                else:
                    self.logger.debug("About to delete job %s from slave %s " % (job_id, slave_id_value))
                    self.adapter.delete_job(job_id)
                del self.__scheduled_shutdowns[slave_id_value]
            else:
                self.logger.debug("Not deleting slave. Slave has already been deleted.")
        else:
            self.logger.debug('Shutdown if no framework: %s: showed up!' % framework_id_value)

    def __delete_channel(self, channel_id):
        self.logger.debug('About to delete channel in %s sec: %s' % 
                          (MesosHandler.CHANNEL_DELETE_WAIT_PERIOD_IN_SECONDS, channel_id))
        gevent.sleep(MesosHandler.CHANNEL_DELETE_WAIT_PERIOD_IN_SECONDS)
        cf = ChannelFactory.get_instance()
        cf.destroy_channel(channel_id)
        self.logger.debug('Channel deleted: %s', channel_id)

    def __delete_framework(self, framework_id_value):
        framework = FrameworkTracker.get_instance().get(framework_id_value)
        if framework is None:
            self.logger.warn("Deleting framework: cannot get framework %s from tracker" % framework_id_value)
            return

        # Acquire framework lock
        self.logger.debug("Deleting framework id %s" % framework_id_value)
        self.__acquire_framework_lock(framework)

        try:
            # Print out the remaining tasks...normally we shouldn't have any
            self.logger.debug("Remaining tasks (normally shouldn't have any unless framework didn't take care of them): %s" %
                              framework.get('task_dict',{}))
            self.logger.debug("Framework jobs: %s" % framework.get('job_ids',[]))
            now = time.time()
            framework['delete_time'] = now

            for slave in framework.get('slave_dict',{}).values():
                self.shutdown_executor(slave)

            self.adapter.unregister_framework(framework)

            # if framework didn't take care of tasks and anythings left
            # mark all of them as FINISHED or KILLED
            for key in framework['task_dict'].keys():
                if framework['task_dict'][key]['state'] != 'TASK_FINISHED':
                    if framework['task_dict'][key]['state'] == 'TASK_STAGING':
                        state = 'TASK_KILLED'
                    else:
                        state = 'TASK_FINISHED'
                    self.logger.debug("Forcing task state to %s for task %s: %s" % \
                               (state, framework['task_dict'][key]['task_info']['name'], framework['task_dict'][key]))
                    # should be set to TASK_KILLED?
                    framework['task_dict'][key]['state'] = state
                    framework['task_dict'][key]['end_time'] = now
            self.logger.trace("framework['task_dict']: %s" % framework['task_dict'])

            # Go through the slaves again removing any scheduled shutdowns
            for slave_id in framework.get('slave_dict',{}).keys():
                self.logger.debug('Checking for slave %s in shutdown list %s' % (slave_id, self.__scheduled_shutdowns))
                if self.__scheduled_shutdowns.get(slave_id):
                    self.logger.debug("Removing queued slave shutdown.  Slave has been deleted.")
                    del self.__scheduled_shutdowns[slave_id]

            # Stop monitoring all of the frameworks jobs
            job_ids = framework.get('job_ids')
            self.logger.debug('Jobs to stop monotiring for: %s' % job_ids)
            if job_ids is not None:
                for job_id in job_ids:
                    if job_id is not None:
                        self.job_monitor.stop_job_monitoring(job_id[0])

            # Add it to our removed frameworks circular buffer
            #self.__finished_frameworks.append(framework_id_value)
            self.logger.debug("Remove framework %s from framework tracker" % framework_id_value)
            FrameworkTracker.get_instance().remove(framework_id_value)
            channel_name = framework['channel_name']
            self.__delete_channel_with_delay(channel_name)

        finally:
            # Release lock
            self.__release_framework_lock(framework)

        return framework

    def __get_framework_info(self, framework):
        framework_info = framework.get('framework_info', {})
        if not len(framework_info):
            framework_info['user'] = framework['user']
            framework_info['name'] = framework['name']
            framework_info['id'] = framework["id"]
            framework_info['failover_timeout'] = framework.get('failover_timeout',0.0)
            framework_info['checkpoint'] = framework.get('checkpoint',False)
            framework_info['role'] = framework.get('role','*')
            framework['framework_info'] = framework_info
        return framework_info

    def __build_launch_tasks_payload(self, framework_id, tasks, http = False):
        payload =  {}
        payload['framework_id'] = framework_id
        # remove agent_id until http executor api implemented
#        for t in tasks:
#            if t.get('agent_id'):
#                self.logger.debug("remove agent_id form task")
#                del t['agent_id']
        payload['tasks'] = tasks
        payload = { "mesos.internal.LaunchTasksMessage" : payload }
        return payload

    def __debit_resources(self, slave, task):
        resources = task['resources']
        self.logger.trace("Task resources: %s" % resources)
        self.logger.trace("Slave before debit: %s" % slave)
        for r in resources:
            if r['name'] == 'ports':
                task_port_range_list = r['ranges'].get('range', [])
                slave_port_range_list = PortRangeUtility.tuple_to_port_range_list(slave['ports'])
                slave_port_range_list = PortRangeUtility.subtract(slave_port_range_list,task_port_range_list)
                slave['ports'] = PortRangeUtility.port_range_to_tuple_list(slave_port_range_list)
            elif r['name'] == 'cpus' or r['name'] == 'mem' or r['name'] == 'disk':
                slave[r['name']] -= r['scalar']['value']
                self.logger.debug('Debiting [%s] of [%s] from slave %s (%s remaining)' % \
                    (r['scalar']['value'], r['name'], slave['id']['value'], slave[r['name']]))
            elif r['type'] == 'SCALAR':
                slave['custom_resources'][r['name']] -= r['scalar']['value']
                self.logger.debug('Debiting [%s] of [%s] from slave %s (%s remaining)' % \
                    (r['scalar']['value'], r['name'], slave['id']['value'], slave['custom_resources'][r['name']]))

        self.logger.trace("Slave after debit: %s" % slave)
        # Record the running task count
        tasks = slave.get('task_count',0)
        tasks += 1
        slave['task_count'] = tasks

    def __credit_resources(self, slave, task):
        resources = task.get('resources', [])
        if len(resources) == 0:
            self.logger.error("No resources to credit from task: %s" % task)
        self.logger.trace("Slave before credit: %s" % slave)
        for r in resources:
            if r['name'] == 'ports':
                task_port_range_list = r['ranges'].get('range', [])
                slave_port_range_list = PortRangeUtility.tuple_to_port_range_list(slave['ports'])
                slave_port_range_list = PortRangeUtility.add(slave_port_range_list,task_port_range_list)
                slave['ports'] = PortRangeUtility.port_range_to_tuple_list(slave_port_range_list)
            elif r['name'] == 'cpus' or r['name'] == 'mem' or r['name'] == 'disk':
                self.logger.debug('Crediting [%s] of [%s] to slave %s' % \
                    (r['scalar']['value'], r['name'], slave['id']['value']))
                slave[r['name']] += r['scalar']['value']
            elif r['type'] == 'SCALAR':
                slave['custom_resources'][r['name']] += r['scalar']['value']
                self.logger.debug('Crediting [%s] of [%s] to slave %s' % \
                    (r['scalar']['value'], r['name'], slave['id']['value']))

        self.logger.trace("Slave after credit: %s" % slave)
        tasks = slave.get('task_count',0)
        tasks -= 1
        slave['task_count'] = tasks

    def __process_task_lost_status_update(self, task, framework, slave_id = None):
        framework_id = framework['id']
        task_dict = framework.get('task_dict', {}) 
        task_id = task['task_id']
        self.logger.debug('Processing task lost for task id %s and framework id %s' % (task_id['value'], framework_id['value']))

        status_update = {}
        status_update['framework_id'] = framework_id
        now = time.time()
        status_update['timestamp'] = now
        status_uuid = self.__generate_uuid()
        status_update['uuid'] = status_uuid
        status_update['status'] = {
            'task_id' : task_id,
            'state' : 'TASK_LOST',
            'uuid' : status_uuid
        }
        if slave_id:
            status_update['status']['slave_id'] = slave_id

        channel = framework['channel_name']
        self.send_status_update(channel, framework, status_update)

        task['state'] = 'TASK_LOST'
        task['lost_time'] = now
        # set task state in framework data to LOST too
        task_dict[task_id['value']]['state'] = 'TASK_LOST'
        # poputale times if happens to be not set
        if 'end_time' not in task_dict[task_id['value']] or len(str(task_dict[task_id['value']]['end_time'])) == 0:
            task_dict[task_id['value']]['end_time'] = now
        if 'start_time' not in task_dict[task_id['value']] or len(str(task_dict[task_id['value']]['start_time'])) == 0:
            task_dict[task_id['value']]['start_time'] = now

        self.__add_delete_element(task_dict, task_id['value'])
        return status_update

    def __initialize_slave_resources(self, framework, slave):
        framework_config = framework['config']
        self.logger.debug('Using framework config for %s : %s' % (framework["name"], framework_config))

        slave['cpus'] = int(framework_config['cpus'])
        slave['mem'] = int(framework_config['mem'])
        slave['disk'] = int(framework_config['disk'])
        slave['ports'] = eval(framework_config['ports'])

        if 'custom_resources' in framework_config:
            slave['custom_resources'] = copy.deepcopy(framework_config['custom_resources'])

    # role excluded with Mesos 1.4.0
    def __build_resources(self, cpus=1, mem=4096, disk=10000, ports=[(31000,32000)], custom_resources=None):
        resource_cpu = {}
        resource_cpu['name'] = "cpus"
        resource_cpu['scalar'] = { 'value': cpus }
        resource_cpu['type'] = "SCALAR"
        #resource_cpu['role'] = "*"

        resource_mem = {}
        resource_mem['name'] = "mem"
        resource_mem['scalar'] = { 'value': mem }
        resource_mem['type'] = "SCALAR"
        #resource_mem['role'] = "*"

        resource_disk = {}
        resource_disk['name'] = "disk"
        resource_disk['scalar'] = { 'value': disk }
        resource_disk['type'] = "SCALAR"
        #resource_disk['role'] = "*"

        resource_ports = {}
        resource_ports['name'] = "ports"
        ranges = []
        for begin,end in ports:
            ranges.append({'begin': begin, 'end':end })
        resource_ports['ranges'] = { 'range': ranges}
        resource_ports['type'] = "RANGES"
        #resource_ports['role'] = "*"

        resources = [resource_cpu, resource_mem, resource_disk, resource_ports]

        if custom_resources is not None:
            for key, val in custom_resources.iteritems():
                resource_dict = {}
                resource_dict['name'] = key
                # if numeric
                if type(val) is int or type(val) is float:
                    resource_dict['scalar'] = { 'value': float(val) }
                    resource_dict['type'] = "SCALAR"
                elif type(val) is list:
                    ranges = []
                    for begin, end in val:
                        ranges.append({'begin': begin, 'end': end})
                    resource_dict['ranges'] = { 'range': ranges}
                    resource_dict['type'] = "RANGES"
                else: # string
                    self.logger.error("Incorrect custom resource type %s for resource %s" % (type(val), key))
                    continue
                    #resource_dict['text'] = { 'value': val }
                    #resource_dict['type'] = "TEXT"
                #resource_dict['role'] = "*"
                self.logger.debug("Custom resource: %s" % resource_dict)
                resources.append(resource_dict)

        return resources

    def __build_attributes(self, attrib, hostname = None):
        attributes = []
        for key in attrib:
            attribute = {}
            attribute['name'] = key
            # for host attribute force to slave hostname if provided
            attribute['text'] = { 'value': hostname if key == 'host' and hostname is not None else attrib[key] }
            attribute['type'] = "TEXT"
            attributes.append(attribute)

        return attributes

    def __build_offer(self, framework, slave, force=False, http=False):
        # If we don't have enough resources to offer than don't
        if not force and (slave['cpus'] == 0 or slave['mem'] == 0 or slave['disk'] == 0):
            self.logger.debug("Build offer: not enough resources to build offer")
            return None
        rt = ResourceTracker.get_instance()
        offer_id = rt.get_unique_offer_id()
        framework_id = framework.get('id')
        slave_id = slave.get('id')

        if slave_id['value'].startswith("place-holder"):
            slave_id['value'] += "-%s" % offer_id
            if not http:
                slave['hostname'] += "-%s" % offer_id

        cpus = int(slave['cpus'])
        mem = int(slave['mem'])
        disk = int(slave['disk'])
        ports = slave['ports']

        offer = {}
        offer['id'] = { 'value': 'offer-%s-%s' % (framework_id['value'], offer_id)}
        offer['framework_id'] = framework_id
        offer['agent_id' if http else 'slave_id'] = slave_id
        offer['hostname'] = slave['hostname']

        offer['resources'] = self.__build_resources(cpus=cpus,mem=mem,
               disk=disk, ports=ports, custom_resources=slave['custom_resources'] if 'custom_resources' in slave else None)

        attributes = self.__build_attributes(framework['attributes'], slave['hostname'])
        if attributes:
            offer['attributes'] = attributes

        # Save the offer in the slave and the framework for future reference
        slave['offer'] = offer
        offers = framework.get('offers',{})
        offers[offer['id']['value']] = offer
        framework['offers'] = offers

        # Update db
        if self.framework_db_interface is not None and self.framework_db_interface.is_active():
            self.framework_db_interface.update_offer_summary(offer)
        return offer

    def send_offers(self, framework, offers):
        payload = {}
        payload['offers'] = offers

        message = ResourceOffersMessage(self.channel.name, payload)

        cf = ChannelFactory.get_instance()
        scheduler_channel_name = framework.get('channel_name')
        scheduler_channel = cf.create_channel(scheduler_channel_name)
        self.logger.debug('Sending offer message via channel %s: %s' % (scheduler_channel_name, message))
        scheduler_channel.write(message.to_json())

    def send_status_update(self, channel_name, framework, update):
        self.logger.trace("send_status_update: channel_name=%s, framework=%s" % (channel_name, framework))
        self.logger.debug("send_status_update: update=%s" % update)
        response = StatusUpdateMessage(self.channel.name,
                     {"update":update} )

        http = True if framework['channel_name'] == "http" else False
        if http:
            # add agent id until http executor api implemented
            status = update['status']
            if 'slave_id' in status:
                status['agent_id'] = status['slave_id']
                del status['slave_id']
            self.logger.debug("HTTP: Sending status: %s" % status)
            http_resp = {'type' : 'UPDATE',
                         'update' : { 'status' : status} }
            offer_event = framework.get('offer_event')
            self.logger.debug("Setting AsyncResult: %s" % repr(offer_event))
            offer_event.set(http_resp)
            gevent.sleep(0)
        else:
            # Forward this to the framework...
            cf = ChannelFactory.get_instance()
            response_channel = cf.create_channel(channel_name)
            self.logger.debug('Sending status update message via channel %s to framework: %s' % (channel_name, response))
            response_channel.write(response.to_json())

    def send_executor_message(self, framework, message):
        response = ExecutorToFrameworkMessage(self.channel.name, message)

        # Forward this to the framework...
        cf = ChannelFactory.get_instance()
        scheduler_channel_name = framework.get('channel_name')
        scheduler_channel = cf.create_channel(scheduler_channel_name)
        self.logger.debug('Sending executor to framework message via channel %s: %s' % (scheduler_channel_name, response))
        scheduler_channel.write(response.to_json())

    def send_framework_message(self, framework, message):
        response = FrameworkToExecutorMessage(self.channel.name, message)

        self.logger.debug("Sending framework message via channel %s: %s" % (self.channel.name, response))
        # Need to get the executor channel
        slave_id = message['slave_id']['value']
        if message['slave_id']['value'].startswith("place-holder"):
            slave_id = framework.get('placeholder_to_slave',{}).get(slave_id)
        slave = framework.get('slave_dict',{}).get(slave_id,{})
        if slave.get('is_command_executor', False):
            task_name = message['executor_id']['value']
            executor_channel = slave['command_executors'].get(task_name,{}).get('channel')
        else:
            executor_channel = slave.get('executor_channel')

        if executor_channel:
            # Forward this to the executor...
            cf = ChannelFactory.get_instance()
            self.logger.debug("Sending framework to executor message via channel %s: %s" %
                              (executor_channel.name, response))
            executor_channel.write(response.to_json())
            return True
        else:
            self.logger.warn("No executor channel to send framework message to.")
            self.logger.debug("Current slaves: %s" % framework.get('slave_dict',{}))
            return False

    def http_shutdown(self, framework_id, executor_id, agent_id):
        framework = FrameworkTracker.get_instance().get(framework_id['value'])
        if framework is None:
            self.logger.warn("Shutdown executor: cannot get framework %s from tracker" % framework_id['value'])
            return

        # Acquire framework lock
        self.logger.debug("Shutdown executor: framework %s, executor=%s, agent=%s" %
                          (framework_id['value'], executor_id['value'], agent_id['value']))
        self.__acquire_framework_lock(framework)

        try:
            slave = framework.get('slave_dict', {}).get(agent_id['value'])
            if not slave:
                self.logger.debug("No slave found for agent: %s" % agent_id['value'])
                return
            # kill all slave tasks
            if slave.get('is_command_executor', False):
                for task in slave.get('command_executors'):
                    self.__kill_task({'task_id' : task}, framework_id, framework)
            else:
                task = slave['executor']['task_id']
                self.__kill_task({'task_id' : task}, framework_id, framework)
            self.shutdown_executor(slave, True)
        except Exception as e:
            self.logger.error("Shutdown executor: exception: %s" % e)
        finally:
            # Release lock
            self.__release_framework_lock(framework)

    def shutdown_executor(self, slave, http = False):
#        response = ShutdownExecutorMessage(self.channel.name, {})
        self.logger.debug("Shutdown executor message for slave: %s" % slave)

        if http:
            http_shutdown = {
                'type' : 'SHUTDOWN'
            }
            ar = slave.get('async_result')
            if ar:
                self.logger.debug("HTTP: Setting AsyncResult: %s" % repr(ar))
                ar.set(http_shutdown)
            else:
                self.logger.warn("HTTP: No executor channels to send message to. Shutdown executor runner instead.")
                self.send_slave_shutdown_message(slave['channel'].name)
            self.update_completed_executor_summary_db(slave)
        else:
            # Need to get the all executors channels
            executor_channels = []
            if slave.get('is_command_executor', False):
                for task_name, val in slave['command_executors'].iteritems():
                    executor_channel = val.get('channel')
                    if executor_channel:
                        executor_channels.append(executor_channel)
                    else:
                        self.logger.warn("No command executor channel for task %s" % task_name)
            else:
                executor_channel = slave.get('executor_channel')
                if executor_channel:
                    executor_channels.append(executor_channel)
                else:
                    self.logger.warn("No custom executor channel")

            # Forward this to the executors...
            if len(executor_channels) != 0:
                response = ShutdownExecutorMessage(self.channel.name, {})
                for executor_channel in executor_channels:
                    self.logger.debug('Sending shutdown executor message via channel %s: %s' %
                                    (executor_channel.name, response))
                    executor_channel.write(response.to_json())
                    self.update_completed_executor_summary_db(slave)
#                return True
                # Delete executor channel
                #self.__delete_channel_with_delay(executor_channel.name)
            else:
                self.logger.warn("No executor channels to send message to. Shutdown executor runner instead.")
                self.send_slave_shutdown_message(slave['channel'].name)
                self.update_completed_executor_summary_db(slave)
#                return False

    def run_task(self, executor_channel, task, framework_info):
        framework_id = framework_info.get('id')
        if task.get('agent_id'):
            del task['agent_id']
        payload = {
            'framework_id' : framework_id,
            'framework'    : framework_info,
            'pid'          : "1234",
            'task'         : task
        }
        message = RunTaskMessage(self.channel.name, payload)

        task_id = task.get('task_id')
        self.logger.debug('Sending run task message to executor via channel %s, task id %s' % (executor_channel.name, task_id))
        executor_channel.write(message.to_json())
        if task.has_key('data'):
            self.logger.debug('Removing data for task id: %s' % task_id)
            del task['data']

    def executor_registered(self, executor_channel, executor_info, framework_id, \
                            framework_info, slave_id, slave_info):
        # Now send our response
        executor_registered = {
          'executor_info' : executor_info,
          'framework_id' : framework_id,
          'framework_info' : framework_info,
          'slave_id' : slave_id,
          'slave_info' : slave_info,
        }
        response_payload = executor_registered
        message = ExecutorRegisteredMessage(self.channel.name, response_payload)

#        cf = ChannelFactory.get_instance()
        self.logger.debug('Sending executor registered message via channel %s: %s' % (executor_channel.name, message))
        executor_channel.write(message.to_json())

    def scale_up(self, framework, tasks = None, scale_count = None):
        framework_config = framework['config']
        if not scale_count:
            scale_count = int(framework_config.get('scale_count', 1))
        self.logger.debug('Scaling up for framework %s by: %d' % (framework['name'], scale_count))
        # Need to submit another runner
        max_tasks = int(framework_config.get('max_tasks'))
        # Check how much headroom we have
        job_headroom = max_tasks - len(framework.get("job_id",[]))
        if job_headroom <= 0:
            self.logger.debug("Scaling up: Not starting any new jobs since the max number of jobs are already pending. (%d/%d)"
                    % (max_tasks,max_tasks))
            return []
        if scale_count > job_headroom:
            self.logger.debug("Scaling up: Only launching %d tasks since there is less headroom than scale level %d" %
                    (job_headroom, scale_count))
            scale_count = job_headroom
        job_ids = self.submit_executor_runner(framework, scale_count, tasks)

        # Add the new ids to the job monitor...
        for j in job_ids:
            # We need actual job id for monitoring, not full tuple
            self.job_monitor.start_job_monitoring(j[0], framework['id']['value'])
        framework_job_ids = framework.get('job_ids', [])
        framework_job_ids = list(set(framework_job_ids).union(job_ids))
        framework['job_ids'] = framework_job_ids
        self.logger.debug("Scaling up: Framework %s has (%d/%d) jobs pending/running" %
                          (framework['name'], len(framework_job_ids), max_tasks))
        return job_ids
        #self.adapter.scale(framework,scale_count)

    def scale_down(self,framework, count=1):
        framework_config = framework['config']
        scale_count = int(framework_config.get('scale_count', count))
        self.logger.debug('Scaling down for framework %s by: %d' % (framework['name'], scale_count))
        scale_count = scale_count * -1
        self.adapter.scale(framework,scale_count)

    def submit_executor_runner(self, framework, concurrent_tasks, tasks = None):
        framework_name = framework['name']
        framework_config = framework['config']
        framework_id = framework['id']
        user = framework['user']

        self.logger.debug('Submit executor runner, framework name: %s' % framework_name)
        scrubbed_framework_name = self.scrub_framework_name(framework_name)

        cf = ChannelFactory.get_instance()
        framework_env = {
            'URB_CONFIG_FILE' : self.executor_runner_config_file,
            'URB_FRAMEWORK_ID' : framework_id['value'],
            'URB_MASTER' : cf.get_message_broker_connection_url(),
            'URB_FRAMEWORK_NAME' : scrubbed_framework_name,
        }
        if framework['channel_name'] == "http":
            framework_env['MESOS_AGENT_ENDPOINT'] = "%s:%d" % (self.service_hostname, self.executor_http_port)

        job_class = framework_config.get('job_class', scrubbed_framework_name)
        job_submit_options = framework_config.get('job_submit_options', '')
        max_tasks = int(framework_config.get('max_tasks', MesosHandler.DEFAULT_FRAMEWORK_MAX_TASKS))
        resource_mapping = framework_config.get('resource_mapping', '')
        executor_runner = framework_config.get('executor_runner', '')
        persistent_volume_claims = framework_config.get('persistent_volume_claims', '')
        try:
            kwargs = {'job_class': job_class,
                      'job_submit_options': job_submit_options,
                      'resource_mapping': resource_mapping,
                      'executor_runner': executor_runner,
                      'persistent_volume_claims': persistent_volume_claims,
                      'tasks': tasks}
            return self.adapter.register_framework(max_tasks, concurrent_tasks,
                                                  framework_env, user, **kwargs)
        except Exception, ex:
            self.logger.error(ex)
            return []

    def rescind_offer(self,framework,offer_id):
        message = {'offer_id' : offer_id }
        response = RescindResourceOfferMessage(self.channel.name, message)
        self.logger.debug('Sending rescind offer message: %s' % response)

        http = True if framework['channel_name'] == "http" else False
        if http:
            http_resp = {'type' : 'RESCIND',
                         'rescind' : offer_id}
            offer_event = framework.get('offer_event')
            self.logger.debug("Setting AsyncResult: %s" % repr(offer_event))
            offer_event.set(http_resp)
        else:
            # Need to get the scheduler channel
            cf = ChannelFactory.get_instance()
            scheduler_channel_name = framework.get('channel_name')
            scheduler_channel = cf.create_channel(scheduler_channel_name)

            scheduler_channel.write(response.to_json())

    def send_kill_task(self, framework_id, slave, task_id, http = False):
        if http:
            kill_event = {
                'type' : 'KILL',
                'kill' : {
                    'task_id' : task_id
                }
            }
            self.logger.debug("HTTP: send_kill_task to executor, before set event")
            slave['async_result'].set(kill_event)
            return True
        else:
            message = {}
            message['framework_id'] = framework_id
            message['task_id'] = task_id
            response = KillTaskMessage(self.channel.name, message)
    #        self.logger.debug("send_kill_task: task=%s, slave=%s" % (task_id, slave))
            if slave.get('is_command_executor', False):
                executor = slave['command_executors'].get(task_id['value'])
                if executor:
                    executor_channel = executor.get('channel')
                else:
                    self.logger.error("Cannot find command executor info in slave for task %s" % task_id['value'])
                    self.logger.debug("Slave: %s" % slave)
            else:
                executor_channel = slave.get('executor_channel')

            if executor_channel:
                self.logger.debug('Sending kill task message via channel %s: %s' % (executor_channel.name, response))
                executor_channel.write(response.to_json())
                return True
            else:
                self.logger.warn('Unable to send kill task on unknown executor')
                return False

    def scrub_framework_name(self, framework_name):
        scrubbed_framework_name = re.sub('[\s|(|)|(:)|(,)|(.)|(^)|($)|(+)|(?)|(\{)|(\})|(\[)|(\])|(\\)|(\()|(\))]+', '',
            framework_name)
        return scrubbed_framework_name

    def __check_type(self, key, value, t):
        ret = False
        for tt in t.split(','):
            self.logger.trace("k=%s, v=%s, t=%s, tt=%s" % (key, value, t, tt))
            if tt == 'num':
                if value.isdigit():
                    return True
            elif tt == 'float':
                if isfloat(value):
                    return True
            elif tt == 'str':
                if isinstance(value, str):
                    return True
            elif tt == 'list_tuple_num':
                lst = []
                try:
                    lst = eval(value)
                    self.logger.trace("lst=%s" % lst)
                except Exception, ex:
                    self.logger.trace("lst exception: %s" % ex)
                    return False
                for l in lst:
                    if isinstance(l, tuple):
                        if not isinstance(l[0], int) or not isinstance(l[1], int):
                            return False
                    else:
                        return False
                return True
            elif tt == 'bool':
                if value in ['True', 'False']:
                    return True
            else:
                self.logger.error("Invalid configuration option type: %s" % tt)
                return False
        self.logger.trace("ret=%s" % ret)
        return ret

    def configure_framework(self, framework):
        cm = ConfigManager.get_instance()
        framework_name = framework['name']
        scrubbed_framework_name = self.scrub_framework_name(framework_name)
        self.logger.debug("Scrubbed framework name: %s" % scrubbed_framework_name)

        framework_config_section = '%sFrameworkConfig' % scrubbed_framework_name
        if not cm.has_config_section('%sFrameworkConfig' % scrubbed_framework_name):
            all_config_sections = cm.get_config_sections()
            self.logger.trace("All sections: %s" % all_config_sections)
            asterisk_config_sections = [ sec for sec in all_config_sections if '*FrameworkConfig' in sec ]
            self.logger.debug("Asterisk config sections: %s" % asterisk_config_sections)
            for re_section in asterisk_config_sections:
                pos = re_section.find('*')
                if pos == -1:
                    self.logger.error("Asterisk wasn't found in config section %s" % re_section)
                    continue
                pattern = re_section[:pos] + '.' + re_section[pos:]
                self.logger.debug("Matching %s pattern" % pattern)
                sec = '%sFrameworkConfig' % scrubbed_framework_name
                if re.match(pattern, sec):
                    framework_config_section = re_section
                    break

        self.logger.info("Using framework config section %s for scrabbed framework %s" % (framework_config_section, scrubbed_framework_name))

        default_config_section = 'DefaultFrameworkConfig'
        framework_config = {}
        for key, t in {
                    'mem' : 'num',
                    'cpus' : 'num,float',
                    'disk' : 'num',
                    'ports' : 'list_tuple_num',
                    'max_rejected_offers' : 'num',
                    'max_tasks' : 'num',
                    'send_task_lost' : 'bool',
                    'scale_count' : 'num',
                    'concurrent_tasks' : 'num',
                    'job_submit_options' : 'str',
                    'initial_tasks' : 'num',
                    'job_class' : 'str',
                    'resource_mapping' : 'str,bool',
                    'executor_runner' : 'str',
                    'persistent_volume_claims' : 'str'
                    }.items():
            value = cm.get_config_option(framework_config_section, key)
            if not value:
                value = cm.get_config_option(default_config_section, key)
            if value is not None:
                if self.__check_type(key, value, t):
                    framework_config[key] = value
                else:
                    self.logger.error("Configuration option: %s=%s invalid type, expected: %s" % (key, value, t))
            else:
                self.logger.debug('config parameter missing: %s' % key)

        # maybe make this generic later...
        for k in ['job_submit_options']:
            if k in framework_config:
                if len(framework_config[k]) != 0:
                    # remove spaces if any from the beginning and end
                    framework_config[k] = framework_config[k].strip()
                    framework_config[k] += " "
                framework_config[k] += framework['ext_data'].get(k,'')

        # get custom resources (custom_resources = dfsio_spindles:8;disk_ids:[(0,5),(10,15)])
        # numeric values or ranges are supported
        key = 'custom_resources'
        value = cm.get_config_option(framework_config_section, key)
        cust_dict = {}
        if value:
            cust_list = value.split(';')
            cust_dict_tmp = dict(cust_list_val.split(':') for cust_list_val in cust_list)
            if cust_dict_tmp:
                for k,v in cust_dict_tmp.iteritems():
                    # if numeric
                    vl = str(v).strip()
                    if vl=='0' or (vl if vl.find('..') > -1 else vl.lstrip('-+').rstrip('0').rstrip('.')).isdigit():
                        cust_dict[k] = float(v)
                    # range
                    else:
                        try:
                            cust_dict[k] = eval(v)
                        except Exception, ex:
                            self.logger.error("Incorrect custom resource format for '%s=%s' (only numeric or range values are supported)" % (k , v))
                framework_config[key] = cust_dict

        key = 'offer_period'
        value = cm.get_config_option(framework_config_section, key)
        if not value:
            value = cm.get_config_option(default_config_section, key)
            if not value:
                value = MesosHandler.DEFAULT_FRAMEWORK_OFFER_WAIT_PERIOD_IN_SECONDS
        framework_config[key] = float(value)

        # Make sure some keys are always there
        job_class = framework_config.get('job_class')
        if job_class is None or len(job_class) == 0:
            self.logger.debug('Using scrubbed framework name as job class')
            job_class = scrubbed_framework_name 
            framework_config['job_class'] = job_class
        self.logger.debug('Framework job class: %s' % job_class)

        max_tasks = framework_config.get('max_tasks')
        if max_tasks is None or int(max_tasks) <= 0:
            self.logger.debug('Using default for max_tasks')
            max_tasks = MesosHandler.DEFAULT_FRAMEWORK_MAX_TASKS
        framework_config['max_tasks'] = int(max_tasks)
        self.logger.debug('Framework max tasks: %s' % max_tasks)

        # config is done
        framework['config'] = framework_config
        self.logger.debug('Framework config: %s' % framework_config)

        # get framework attributes (attributes = host:host1;rack:rack1)
        key = 'attributes'
        value = cm.get_config_option(framework_config_section, key)
        framework_attributes = {}
        if value:
            attr_list = value.split(';')
            framework_attributes = dict(attr_list_val.split(':') for attr_list_val in attr_list)
        self.logger.debug('Framework attributes: %s' % framework_attributes)
        framework['attributes'] = framework_attributes

    def send_slave_shutdown_message(self, slave_channel_name):
        cf = ChannelFactory.get_instance()
        slave_channel = cf.create_channel(slave_channel_name)
        self.logger.debug('Sending shutdown to slave: %s' %
            slave_channel_name)
        message = SlaveShutdownMessage(self.channel.name, {})
        slave_channel.write(message.to_json())

    def send_service_disconnected_message(self):
        cf = ChannelFactory.get_instance()
        channel_names = cf.get_channel_names('*.notify')
        self.logger.debug('Sending service disconnected messages, list of existing notify channels: %s' %
            channel_names)
        message = ServiceDisconnectedMessage(self.channel.name, {})
        for channel_name in channel_names:
            channel = cf.create_channel(channel_name)
            self.logger.debug('Sending service disconnected message to %s' %
                channel_name)
            channel.write(message.to_json())
            self.channel_monitor.start_channel_monitoring(channel_name)

    def update_event_db(self, request):
        if self.event_db_interface is None or not self.event_db_interface.is_active():
            return
        event_id = request.get('message_id')
        target = request.get('target')
        event_name = target
        event_info = {'id' : event_id, 'name' : event_name}

        # Figure out framework id
        framework_id = None
        payload = request.get('payload')
        if payload is not None:
            mesos_message = 'mesos.internal.%s' % target
            message = payload.get(mesos_message)
            if message is not None:
                framework_id = message.get('framework_id')
        if framework_id is not None: 
            event_info['framework_id'] = framework_id['value']
        self.logger.debug('Updating event db for message id %s' % event_id)
        self.event_db_interface.update_event(event_info)

    def update_framework_db(self, request):
        framework_id = FrameworkTracker.get_instance().retrieve_and_forget_request_framework_id(request)
        if self.framework_db_interface is not None and self.framework_db_interface.is_active():
            self.logger.debug('Updating framework db for message id %s' % request.get('message_id'))
            self.framework_db_interface.update_framework(framework_id)
        return framework_id

    def update_completed_executor_summary_db(self, slave):
        if self.framework_db_interface is not None and self.framework_db_interface.is_active():
            slave_id = slave['id']['value']
            executor_id = 'executor-%s' % slave_id
            self.logger.debug('Updating executor summary db after shutdown for slave id %s' % slave_id)
            self.framework_db_interface.update_completed_executor_summary(executor_id)

    def http_request(self, framework_id, agent_id, resources):
        self.logger.debug("http_request")

    def http_subscribe_executor(self, content):
        framework_id_value = content['framework_id']['value']
        executor_id_value = content['executor_id']['value']
        unacknowledged_tasks = content['subscribe'].get('unacknowledged_tasks')
        unacknowledged_updates = content['subscribe'].get('unacknowledged_updates')
        self.logger.info("HTTP: Subscribe executor for framework id %s and executor id %s" %
                         (framework_id_value, executor_id_value))
        framework = FrameworkTracker.get_instance().get(framework_id_value)
        if not framework:
            self.logger.error("No framework with id: %s" % framework_id_value)
            return {}, {}
        self.logger.debug("Current framework: %s" % framework)
        if unacknowledged_tasks:
            self.logger.warn("There are unacknowledged tasks: %s" % unacknowledged_tasks)
        if unacknowledged_updates:
            self.logger.warn("There are unacknowledged updates: %s" % unacknowledged_updates)

        payload = {
             'mesos.internal.RegisterExecutorMessage' : {
                 'executor_id' : content['executor_id'],
                 'framework_id' : content['framework_id'],
             }
        }
        request = {
            'source_id' : None, # indicate http type
            'reply_to' : 'http',
            'message_id' : str(uuid.uuid1()),
            'payload' : payload
            }

        subscribed, tasks = self.register_executor(request)
        self.__release_framework_lock(framework)
        return subscribed, tasks

    def http_update_executor(self, content):
        self.logger.info("HTTP: Update from executor for framework id %s and executor id %s" %
                         (content['framework_id']['value'], content['executor_id']['value']))
        update = content['update']
        update['executor_id'] = content['executor_id']
        update['framework_id'] = content['framework_id']
        payload = {
             'mesos.internal.StatusUpdateMessage' : {
                 'update' : content['update']
             }
        }
        request = {
            'source_id' : None, # indicate http type
            'reply_to' : 'http',
            'message_id' : str(uuid.uuid1()),
            'payload' : payload
            }

        framework, _ = self.status_update(request)
        if framework:
            self.__release_framework_lock(framework)
        gevent.sleep(0)

    def http_message_executor(self, content):
        self.logger.info("HTTP: Message from executor for framework id %s and executor id %s" %
                         (content['framework_id']['value'], content['executor_id']['value']))
        framework_id_value = content['framework_id']['value']
        framework = FrameworkTracker.get_instance().get(framework_id_value)
        if not framework:
            self.logger.error("No framework with id: %s" % framework_id_value)
            return
        self.logger.debug("Current framework: %s" % framework)
        
        payload = {
             'mesos.internal.ExecutorToFrameworkMessage' : {
                 'framework_id' : content['framework_id'],
                 'agent_id' : { 'value' : 'dummy' }, # TODO: find a way to get agent_id
                 'executor_id' : content['executor_id'],
                 'data' : content['message']['data']
             }
        }
        request = {
            'source_id' : None, # indicate http type
            'reply_to' : 'http',
            'message_id' : str(uuid.uuid1()),
            'payload' : payload
            }

        framework, _ = self.executor_to_framework(request)
        if framework:
            self.__release_framework_lock(framework)
        self.logger.debug("HTTP: Message from executor for framework end")

    def http_handle_executor(self, content, agent_id):
        framework_id_value = content['framework_id']['value']
        executor_id_value = content['executor_id']['value']
        agent_id_value = agent_id['value']
        self.logger.info("HTTP: Starting executor events handler loop for framework %s, executor %s, agent %s" %
                         (framework_id_value, executor_id_value, agent_id_value))
        framework = FrameworkTracker.get_instance().get(framework_id_value)
        slave = framework['slave_dict'].get(agent_id_value)
        slave['async_result'] = gevent.event.AsyncResult()
        while True:
            try:
                framework = FrameworkTracker.get_instance().get(framework_id_value)
                self.logger.debug("framework: %s" % framework)
                if framework is None:
                    if self.framework_db_interface is not None and self.framework_db_interface.is_active():
                        self.framework_db_interface.set_framework_summary_status_inactive(framework_id_value)
                    self.logger.info("Framework id %s is not active, exiting executor events loop" % framework_id_value)
                    break

                if not self.__master_broker:
                    # In case we need to restart when we reregister,
                    # remove offer event
                    self.logger.debug("No master broker")
#                    if framework.has_key('offer_event'):
#                        self.logger.debug("Deleting offer event: %s" % framework['offer_event'])
#                        del framework['offer_event']
                    break

#                self.__acquire_framework_lock(framework)
#                slave = framework['slave_dict'].get(agent_id_value)
#                slave['async_result'] = gevent.event.AsyncResult()
                self.logger.debug("HTTP: executor event loop: before wait on %s" % repr(slave['async_result']))
                slave['async_result'].wait()
                data = slave['async_result'].value
                if data:
                    yield data
                    self.logger.debug("After yielded data")

                self.logger.debug("HTTP: executor event loop: renew AsyncResult, old=%s" % repr(slave['async_result']))
#                self.__acquire_framework_lock(framework)
                del framework['slave_dict'][agent_id_value]['async_result']
                framework['slave_dict'][agent_id_value]['async_result'] = gevent.event.AsyncResult()
                slave = framework['slave_dict'].get(agent_id_value)
#                self.__release_framework_lock(framework)
                self.logger.debug("New executor AsyncResult=%s" % repr(framework['slave_dict'][agent_id_value]['async_result']))

            except Exception, ex:
                self.logger.error("Exception in executor events loop for framework id %s and executor_id %s" %
                                  (framework_id_value, executor_id_value))
                self.logger.exception(ex)
            finally:
                # Release lock
                self.logger.debug("In finally before release lock")
 #               self.__release_framework_lock(framework)
 
        self.logger.info("HTTP: Exiting executor events loop for framework id %s" %(framework_id['value']))


# Testing
if __name__ == '__main__':
    pass
