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


import re
import os
import os.path
import stat
import sys
import time
import gevent
import json
import socket
import uuid

from urb.exceptions.configuration_error import ConfigurationError
from urb.config.config_manager import ConfigManager
from urb.utility.naming_utility import NamingUtility
from urb.messaging.channel_factory import ChannelFactory
from urb.messaging.messaging_utility import MessagingUtility
from urb.log.log_manager import LogManager
from executor_handler import ExecutorHandler
from urb.messaging.mesos.register_executor_runner_message import RegisterExecutorRunnerMessage
from urb.messaging.heartbeat_message import HeartbeatMessage

class ExecutorRunner:
    """ executor runner class. """

    SECONDS_TO_WAIT_FOR_GREENLETS = 3
    HEARTBEAT_PERIOD_IN_SECONDS = 60

    def __init__(self, defaults={}):
        self.done = False
        # Config manager
        ConfigManager.get_instance().set_config_defaults(defaults)
        self.configure()

    def configure(self):
        cm = ConfigManager.get_instance()
        self.service_monitor_endpoint = cm.get_config_option('ExecutorRunner',
            'service_monitor_endpoint')
        mesos_master_endpoint = cm.get_config_option('ExecutorRunner',
            'mesos_master_endpoint')
        self.mesos_work_dir = cm.get_config_option('ExecutorRunner',
            'mesos_work_dir')  % { 'tmp' : os.environ.get('TMP','') }

        # Create our working directory before we start logging
        if not os.path.exists(self.mesos_work_dir):
            os.makedirs(self.mesos_work_dir)
        os.chdir(self.mesos_work_dir)

        self.logger = LogManager.get_instance().get_logger(self.__class__.__name__)
        self.logger.debug('Config file: %s' % cm.get_config_file())

        cf = ChannelFactory.get_instance()
        self.service_monitor_channel = cf.create_channel(self.service_monitor_endpoint)
        self.mesos_channel = cf.create_channel(mesos_master_endpoint)
        self.channel_name = cf.get_unique_channel_name()
        self.logger.debug('Got my channel name: %s' % self.channel_name)
        self.host = cf.get_message_broker_connection_host()
        self.port = cf.get_message_broker_connection_port()
        # The service will send messages to our notify channel
        channel_id = MessagingUtility.get_endpoint_id(self.channel_name)
        self.notify_channel_name = MessagingUtility.get_notify_channel_name(None,channel_id)
        self.handler_list = [ExecutorHandler(self.notify_channel_name,self)]
    
        # Get various id objects
        self.framework_id = {
            'value' : os.environ['URB_FRAMEWORK_ID']
        }

        if 'JOB_ID' in os.environ:
            self.job_id = os.environ['JOB_ID']
            self.task_id = os.environ.get('SGE_TASK_ID', '1')
            slave_id = NamingUtility.create_slave_id(self.job_id, self.task_id, self.notify_channel_name)
        else:
            self.job_id = uuid.uuid1().hex
            self.logger.error('Environment variable JOB_ID is not defined, autogenerating job id: ' % self.job_id)
            self.task_id = "1"
            slave_id = NamingUtility.create_slave_id(self.job_id, self.task_id , self.notify_channel_name)

        self.slave_id = {
            "value" : slave_id
        }

        self.logger.debug('slave id: %s' % self.slave_id)
        self.slave_info = {
            'hostname' : self.host,
            'port' : self.port,
            'id' : self.slave_id
        }

        self.dummy_framework_info = {
            'name':'default',
            'user':'default',
        }

        self.heartbeat_channel_info = {
            'channel_id' : self.notify_channel_name,
            'framework_id' : self.framework_id['value'],
            'slave_id' : self.slave_id['value'],
            'endpoint_type' : 'executor_runner',
        }

    def send_heartbeat(self):
        try: 
            self.logger.debug('Sending heartbeat to %s via channel %s' %
                              (self.service_monitor_endpoint, self.channel_name))
            payload = {'channel_info' : self.heartbeat_channel_info}
            message = HeartbeatMessage(self.channel_name, payload)
            self.service_monitor_channel.write(message.to_json())
        except Exception, ex:
            self.logger.error('Could not send heartbeat: %s', ex)

    def register_executor_runner(self,tasks=None):
        payload = {}
        payload['slave_id'] = self.slave_id
        payload['framework_id'] = self.framework_id
        host = socket.gethostname()
        # use ip address if in k8s pod
        payload['host'] = host if not os.environ.get('KUBERNETES_SERVICE_HOST') else socket.gethostbyname(host)
        payload['port'] = 0
        payload['job_id'] = self.job_id
        payload['task_id'] = self.task_id
        # These are only the *initial* tasks... we can't really use them for reregister
        if tasks is not None:
            payload['tasks'] = tasks
        message = RegisterExecutorRunnerMessage(self.channel_name, payload)
        self.logger.debug('Sending RegisterExecutorRunnerMessage via channel %s: %s' 
                        % (self.channel_name, message))
        self.mesos_channel.write(message.to_json())

    def run(self, time_in_seconds=0):
        """ Run executor. """
        start_time = time.time()
        end_time = None
        if time_in_seconds > 0:
            end_time = start_time + time_in_seconds

        self.logger.debug('Starting listeners')
        handler_listeners = []
        for handler in self.handler_list:
            self.logger.debug('Starting listener: %s' % handler)
            handler_listener = handler.listen()
            handler_listeners.append(handler_listener)

        self.logger.info('Notifying master')
        self.register_executor_runner()

        self.logger.info('Waiting for requests')
        # Lets wait a a bit before sending our first heartbeat so 
        # the server has a chance to process or registration messages first
        last_heartbeat_time = time.time() - ExecutorRunner.HEARTBEAT_PERIOD_IN_SECONDS / 3
        while not self.done:
            now = time.time()
            if end_time is not None:
                if now > end_time:
                    self.logger.info('Done serving requests')
                    break
            # Send heartbeat
            if now > last_heartbeat_time + ExecutorRunner.HEARTBEAT_PERIOD_IN_SECONDS:
                last_heartbeat_time = now
                self.send_heartbeat()
            gevent.sleep(0.001)
            gevent.joinall(handler_listeners, 
                timeout=ExecutorRunner.SECONDS_TO_WAIT_FOR_GREENLETS)
        self.logger.info('Executor done')

    def run_forever(self):
        self.run()
        self.logger.debug('run_forever done')

# Run server.
def run():
#    from gevent import monkey; monkey.patch_all()
    from gevent import monkey; monkey.patch_socket()
    logger = LogManager.get_instance().get_logger(__name__)
    logger.debug("run begins")
    try:
        executor = ExecutorRunner()
        executor.run()
    except KeyboardInterrupt, ex:
        logger.info('KeyboardInterrupt: %s' % ex)
        pass
    logger.info('Executor runner exit')
            
# Testing
if __name__ == '__main__':
#    from gevent import monkey; monkey.patch_all()
    from gevent import monkey; monkey.patch_socket()
    run()
 
