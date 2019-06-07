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


from urb.adapters.adapter_interface import Adapter
from urb.config.config_manager import ConfigManager
from urb.log.log_manager import LogManager
from urb.exceptions.unknown_job import UnknownJob
import gevent
import subprocess
import uuid
import os

class LocalhostAdapter(Adapter):
    """ Local host Adapter class. """

    DELETE_WAIT_PERIOD_IN_SECONDS = 2.0

    def __init__(self):
        self.logger = LogManager.get_instance().get_logger(
            self.__class__.__name__)
        self.channel_name = None
        self.configure()

    def configure(self):
        self.logger.debug('configure')
        cm = ConfigManager.get_instance()
        self.executor_runner_path = cm.get_config_option('ExecutorHandler', 'executor_runner_path', 'executor-runner')

    def set_channel_name(self, channel_name):
        self.logger.debug('set_channel_name')
        self.channel_name = channel_name

    def authenticate(self, request):
        self.logger.debug('Authenticate: %s' % request)

    def deactivate_framework(self, request):
        self.logger.debug('Deactivate framework: %s' % request)

    def exited_executor(self, request):
        self.logger.debug('Exited executor: %s' % request)

    def kill_task(self, request):
        self.logger.debug('Kill task: %s' % request)

    def launch_tasks(self, framework_id, tasks, *args, **kwargs):
        self.logger.debug('Launch tasks for framework id: %s' % framework_id)

    def reconcile_tasks(self, request):
        self.logger.debug('Reconcile tasks: %s' % request)
        # indicates that job status cannot be reasonably retrieved in get_job_status
        return (False, 0)

    def register_executor_runner(self, framework_id, slave_id, *args,
            **kwargs):
        self.logger.debug(
            'Register executor runner for framework id %s, slave id %s' %
            (framework_id, slave_id))

    def register_framework(self, max_tasks, concurrent_tasks, framework_env, user=None, *args, **kwargs):
        self.logger.info("register_framework: max_tasks=%s, concurrent_tasks=%s, framework_env=%s, user=%s, kwargs: %s" %
                         (max_tasks, concurrent_tasks, framework_env, user, kwargs))
        cmd = self.executor_runner_path
        env = framework_env
        job_ids = []
        for i in range(0,concurrent_tasks):
            if i >= max_tasks:
                break
            job_id = str(uuid.uuid1().time_low)
            # TMP environment variable is executor runner working directory
            env["TMP"] = os.path.join("/tmp", job_id)
            env["JOB_ID"] = job_id
            self.logger.info('Submit job: command: %s' % cmd)
            p = subprocess.Popen([cmd], shell = True, executable = "/bin/bash", env = env)
            pid = p.pid
            self.logger.info('Submitted job_id: %s, pid: %s' % (job_id, pid))
            jid_tuple = (job_id,pid,None)
            job_ids.append(jid_tuple)
        return job_ids

    def register_slave(self, request):
        self.logger.debug('Register slave: %s' % request)

    def reregister_framework(self, request):
        self.logger.debug('Reregister framework: %s' % request)

    def reregister_slave(self, request):
        self.logger.debug('Reregister slave: %s' % request)

    def resource_request(self, request):
        self.logger.debug('Resource request: %s' % request)

    def revive_offers(self, request):
        self.logger.debug('Revive offers: %s' % request)

    def submit_scheduler_request(self, request):
        self.logger.debug('Submit scheduler request: %s' % request)

    def status_update_acknowledgement(self, request):
        self.logger.debug('Status update acknowledgement: %s' % request)

    def status_update(self, request):
        self.logger.debug('Status update: %s' % request)

    def scale(self, framework, count):
        self.logger.debug('scale: framework=%s, count=%s' % (framework, count))

    def unregister_framework(self, framework):
        self.logger.debug('Unregister framework: %s' % framework['name'])
        self.delete_jobs_delay(framework)

    def __delete_jobs_delay(self, framework):
        # Delete all jobs
        job_ids = framework.get('job_ids')
        if job_ids is not None:
            # Spawn job to make sure the actual executors exit...
            gevent.spawn(self.__delete_jobs, job_ids)

    def __delete_jobs(self, job_ids):
        for job_id in job_ids:
            try:
                self.delete_job(job_id)
            except Exception as ex:
                self.logger.warn("Error deleting job: %s" % ex)

    def __delete_job(self, job_id):
        if len(str(job_id[0])) != 0:
            pid = str(job_id[1])
            self.logger.debug('Request deleting job: %s', job_id)
            subprocess.Popen(["kill", pid])
            gevent.sleep(LocalhostAdapter.DELETE_WAIT_PERIOD_IN_SECONDS)
            ret = subprocess.call(["ps", pid])
            if ret == 0:
                self.logger.debug('Still running, deleting job %s with pid %s with -9 signal', (job_id[0], pid))
                subprocess.call(["kill", "-9", pid])
        else:
            self.logger.error("Deleting job: '%s' - empty job id", job_id)

    def get_job_id_tuple(self, job_id):
        # Try to get job status
        self.logger.debug('get_job_id_tuple for job_id %s', job_id)
        return (job_id,None,None)

    def get_job_status(self, job_id):
        self.logger.debug('Getting status for job: %s', job_id)
        pid = job_id[1]
        ret = subprocess.call(["ps", pid])
        if ret != 0:
            raise UnknownJob('Unknown job id: %s' % job_id)

    def get_job_accounting(self, job_id):
        self.logger.debug('Getting accounting for job: %s', job_id)
        acct = {}
        return acct

    def unregister_slave(self, request):
        self.logger.debug('Unregister slave: %s' % request)


# Testing
if __name__ == '__main__':
    adapter = LocalhostAdapter()
    print 'Done'


