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


import abc
from urb.log.log_manager import LogManager

class Adapter(object):
    __metaclass__ = abc.ABCMeta

    # Singleton.
    __instance = None

    def __new__(cls, *args, **kwargs):
        # Allow subclasses to create their own instances.
        if cls.__instance is None or cls != type(cls.__instance):
            instance = object.__new__(cls, *args, **kwargs)
#            instance.__init__()
            cls.__instance = instance
        return cls.__instance

    @abc.abstractmethod
    def authenticate(self, request):
        self.logger.trace('Authenticate: %s' % request)

    @abc.abstractmethod
    def deactivate_framework(self, request):
        self.logger.trace('Deactivate framework: %s' % request)

    @abc.abstractmethod
    def exited_executor(self, request):
        self.logger.trace('Exited executor: %s' % request)

    @abc.abstractmethod
    def kill_task(self, request):
        self.logger.trace('Kill task: %s' % request)

    @abc.abstractmethod
    def launch_tasks(self, framework_id, tasks, *args, **kwargs):
        self.logger.trace('Launch tasks: %s for framework id: %s' % (tasks, framework_id))

    @abc.abstractmethod
    def reconcile_tasks(self, request):
        self.logger.trace('Reconcile tasks: %s' % request)

    @abc.abstractmethod
    def register_executor_runner(self, framework_id, slave_id, *args, **kwargs):
        self.logger.trace('Register executor runner for framework id %s, slave id %s' %
                          (framework_id, slave_id))

    @abc.abstractmethod
    def register_framework(self, max_tasks, concurrent_tasks, framework_env, user, *args, **kwargs):
        self.logger.debug('Register framework: max_tasks=%s, concurrent_tasks=%s, framework_env=%s, user=%s' %
                          (max_tasks, concurrent_tasks, framework_env, user))

    @abc.abstractmethod
    def register_slave(self, request):
        self.logger.trace('Register slave: %s' % request)

    @abc.abstractmethod
    def reregister_framework(self, request):
        self.logger.trace('Reregister framework: %s' % request)

    @abc.abstractmethod
    def reregister_slave(self, request):
        self.logger.trace('Reregister slave: %s' % request)

    @abc.abstractmethod
    def resource_request(self, request):
        self.logger.trace('Resource request: %s' % request)

    @abc.abstractmethod
    def revive_offers(self, request):
        self.logger.trace('Revive offers: %s' % request)

    @abc.abstractmethod
    def status_update_acknowledgement(self, request):
        self.logger.trace('Status update acknowledgement: %s' % request)

    @abc.abstractmethod
    def status_update(self, request):
        self.logger.trace('Status update: %s' % request)

    @abc.abstractmethod
    def scale(self, framework, count):
        self.logger.trace('Scale: framework: %s, count=%s' % (framework, count))

    @abc.abstractmethod
    def unregister_framework(self, framework):
        self.logger.debug('Unregister framework: %s' % framework['name'])
        self.delete_jobs_delay(framework)

    @abc.abstractmethod
    def delete_jobs_delay(self, framework):
        self.logger.debug('Deleting job with delay for framework: %s', framework)

    @abc.abstractmethod
    def delete_jobs(self, job_ids):
        self.logger.debug('Deleting jobs: %s', job_ids)

    @abc.abstractmethod
    def delete_job(self, job_id):
        self.logger.debug('Deleting job: %s', job_id)

    @abc.abstractmethod
    def get_job_id_tuple(self, job_id):
        # Get job status and extract task array info (job_id, first_array_id, step)
        # If job is not task array return tuple (job_id, None, None)
        # In addition to job_id in two other fields a tuple can contain
        # different useful information about the job
        self.logger.debug('get_job_id_tuple job: %s', job_id)

    @abc.abstractmethod
    def get_job_accounting(self, job_id):
        self.logger.debug('Getting accounting for job: %s', job_id)

    @abc.abstractmethod
    def unregister_slave(self, request):
        self.logger.debug('Unregister slave: %s' % request)


# Testing
if __name__ == '__main__':
    print 'Done'
