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


import gevent
from gevent import event
from urb.utility.job_tracker import JobTracker
from urb.log.log_manager import LogManager
from urb.config.config_manager import ConfigManager
from urb.exceptions.pending_job import PendingJob

class JobMonitor(object):
    """ Job monitor class. """

    GREENLET_SLEEP_PERIOD_IN_SECONDS = 0.001
    MONITOR_POLL_PERIOD_IN_SECONDS = 15.0
    MAX_JOB_STATUS_RETRIEVAL_ERROR_COUNT = 3
    JOB_REMOVAL_DELAY_IN_SECONDS = 5

    def __init__(self, adapter, job_status_update_callback, 
            job_delete_callback, job_accounting_update_callback):
        self.__monitor = False
        self.__thread_event = gevent.event.Event()
        self.logger = LogManager.get_instance().get_logger(
            self.__class__.__name__)
        self.adapter = adapter
        self.job_status_update_callback = job_status_update_callback
        self.job_delete_callback = job_delete_callback
        self.job_accounting_update_callback = job_accounting_update_callback 

        # Configuration
        cm = ConfigManager.get_instance()
        self.max_job_status_retrieval_count = int(cm.get_config_option('JobMonitor', 'max_job_status_retrieval_count', JobMonitor.MAX_JOB_STATUS_RETRIEVAL_ERROR_COUNT)) 
        self.logger.debug('Using max job status retrieval count: %s' % self.max_job_status_retrieval_count) 
        self.monitor_poll_period_in_seconds = float(cm.get_config_option('JobMonitor', 'monitor_poll_period_in_seconds', JobMonitor.MONITOR_POLL_PERIOD_IN_SECONDS))
        self.logger.debug('Using monitor poll period: %s [seconds]' % self.monitor_poll_period_in_seconds) 

    def start_job_monitoring(self, job_id, framework_id):
        self.logger.debug('Start monitoring job id %s for framework id %s' % (
            job_id, framework_id))
        job_info = {
            'framework_id' : framework_id, 
            'monitor_job'  : True
        }
        JobTracker.get_instance().add(job_id, job_info)

    def stop_job_monitoring(self, job_id):
        self.logger.debug('Stop monitoring job id %s' % (job_id))
        job_info = JobTracker.get_instance().get(job_id)
        if job_info is not None:
            job_info['monitor_job'] = False

    def __remove_job_from_tracker(self, job_id, framework_id):
        # Remove job from tracker.
        self.logger.debug('Removing job id %s from tracker' % job_id)
        JobTracker.get_instance().remove(job_id)
        try:
            self.job_delete_callback(job_id, framework_id)
        except Exception as ex:
            self.logger.error(
                'Error invoking delete callback for job id %s: %s' % (job_id, ex))

    def __retrieve_job_accounting_and_remove_job_from_tracker(self, job_id, job_info):
        cnt = job_info.get('accounting_retrieval_count', 0)
        cnt += 1
        job_info['accounting_retrieval_count'] = cnt
        framework_id = job_info['framework_id']
        job_accounting = self.adapter.get_job_accounting(job_id)
        self.logger.debug('Job accounting: %s' % job_accounting) 
        self.job_accounting_update_callback(job_id, framework_id, job_accounting)
        if len(job_accounting) > 0:
            self.logger.debug('Job accounting retrieved, job %s is done' % job_id)
            self.__remove_job_from_tracker(job_id, framework_id)
        elif cnt > self.max_job_status_retrieval_count:
            self.logger.debug('Job accounting retrieval count exceeded %s' % 
                self.max_job_status_retrieval_count)
            self.__remove_job_from_tracker(job_id, framework_id)

    def __handle_job_status_retrieval_error(self, job_id, job_info):
        cnt = job_info.get('status_retrieval_error_count', 0)
        cnt += 1
        job_info['status_retrieval_error_count'] = cnt
        framework_id = job_info['framework_id']
        job_accounting = self.adapter.get_job_accounting(job_id)
        self.logger.debug('Job accounting: %s' % job_accounting) 
        self.job_accounting_update_callback(job_id, framework_id, job_accounting)
        if len(job_accounting) > 0:
            self.logger.debug('Job accounting retrieved, job %s is done' % 
                job_id)
            self.__remove_job_from_tracker(job_id, framework_id)
        elif cnt > self.max_job_status_retrieval_count:
            self.logger.debug('Job status retrieval error count exceeded %s' % 
                self.max_job_status_retrieval_count)
            self.__remove_job_from_tracker(job_id, framework_id)

    def monitor(self):
        """ Monitoring thread. """
        self.logger.debug('Entering job monitoring loop')
        while True:
            if not self.__monitor:
                break
            self.__thread_event.clear()
            job_id_list = JobTracker.get_instance().keys()
            for job_id in job_id_list:
                job_info = None
                try:
                    job_info = JobTracker.get_instance().get(job_id)
                    if job_info is None:
                        continue
                    framework_id = job_info['framework_id']
                    if job_info['monitor_job']:
                        self.logger.debug('Getting status for job id %s' % job_id)
                        job_status = self.adapter.get_job_status(job_id)
                        self.logger.trace('Job id %s status: %s' % (job_id, job_status))
                        job_info['job_status'] = job_status
                        # Got status, call framework callback
                        # this should throw exception to stop job monitoring
                        self.job_status_update_callback(job_id, framework_id, job_status)
                    else:
                        # We are no longer monitoring this job.
                        #self.__remove_job_from_tracker(job_id, framework_id)
                        self.__retrieve_job_accounting_and_remove_job_from_tracker(job_id, job_info)
                except PendingJob as ex:
                    self.logger.debug('Job monitor: job %s is pending: %s' % (job_id, ex))
                # handles jobs completion (UnknownJob for UGE and CompletedJob for k8s)
                except Exception as ex:
                    self.logger.debug('Jon monitor: job %s likely completed: %s' % (job_id, ex))
                    if job_info is not None:
                        self.__handle_job_status_retrieval_error(job_id, 
                            job_info)
                # Must allow other greenlets to run.
                gevent.sleep(JobMonitor.GREENLET_SLEEP_PERIOD_IN_SECONDS)

            # Monitoring thread sleep
            self.__thread_event.wait(self.monitor_poll_period_in_seconds) 

        self.logger.debug('Exiting job monitor loop')

    def stop(self):
        """ Stop monitor. """
        self.logger.info("Job monitor: stopping")
        self.__monitor = False
        self.__thread_event.set()
        self.__monitor_thread.join()
        self.logger.debug("Job monitor: after join")
        
    def start(self):
        """ Start monitor. """
        self.__monitor = True
        self.__monitor_thread = gevent.spawn(self.monitor)
        return self.__monitor_thread
        
    def is_monitoring(self):
        """ Are we monitoring jobs? """
        return self.__monitor
        
# Testing
if __name__ == '__main__':
    print('Done')

