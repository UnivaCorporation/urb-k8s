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



from urb.log.log_manager import LogManager
from urb.utility.framework_tracker import FrameworkTracker
from urb.utility.job_tracker import JobTracker
from gevent import lock
import time

class FrameworkDBInterface(object):
    """Class responsible for updating frameworks in db."""

    def __init__(self, db_client):
        self.logger = LogManager.get_instance().get_logger(self.__class__.__name__)
        self.db_client = db_client
        curr_ttl = -1
        try:
            index_info = self.db_client.get_index_information('events')
            self.logger.trace('index_info=%s' % index_info)
            if 'ttl_index' in index_info:
                if 'key' in index_info['ttl_index'].keys():
                    if 'timestamp' in index_info['ttl_index']['key'][0]:
                        curr_ttl = index_info['ttl_index']['expireAfterSeconds']
                        self.logger.debug('Current Mongo TTL: %s ' % curr_ttl)
            if curr_ttl == -1:
                self.logger.debug("No 'expireAfterSeconds' in index information for 'events' collection")
        except Exception, ex:
            self.logger.warn('Cannot get index info: %s' % ex)

        ttl_sec = self.db_client.expire * 31 * 24 * 60 * 60
        # drop TTL indexes if ttl set to 0
        if self.db_client.expire == 0 and curr_ttl != -1:
            self.logger.info('Dropping Mongo TTL indexes')
            try:
                self.db_client.drop_ttl_index('events')
                self.db_client.drop_ttl_index('executor_summaries')
                self.db_client.drop_ttl_index('framework_summaries')
                self.db_client.drop_ttl_index('frameworks')
                self.db_client.drop_ttl_index('offer_summaries')
                self.db_client.drop_ttl_index('task_summaries')
                self.logger.info("Done")
            except Exception, ex:
                self.logger.warn('Cannot drop Mongo TTL indexes: %s' % ex)
        elif self.db_client.expire != 0 and curr_ttl != ttl_sec:
            self.logger.info('Setting Mongo TTL to %s months or %s sec' % (str(self.db_client.expire), str(ttl_sec)))
            try:
                self.db_client.create_ttl_index('events', 'timestamp', ttl_sec)
                self.db_client.create_ttl_index('executor_summaries', 'stopped', ttl_sec)
                self.db_client.create_ttl_index('framework_summaries', 'unregistered', ttl_sec)
                self.db_client.create_ttl_index('frameworks', 'unregistered_time', ttl_sec)
                self.db_client.create_ttl_index('offer_summaries', 'timestamp', ttl_sec)
                self.db_client.create_ttl_index('task_summaries', 'stopped', ttl_sec)
                self.logger.info("Done")
            except Exception, ex:
                self.logger.warn('Cannot set Mongo TTL for %s sec: %s', (ttl_sec, ex))
        else:
            self.logger.debug("Mongo TTL didn't change")

    def find_framework(self, framework_id):
        return self.db_client.find_one('frameworks', {'_id' : framework_id})

    def find_executor_summary(self, executor_id, running = None):
        if running is None:
            return self.db_client.find_one('executor_summaries', {'_id' : executor_id})
        else:
            return self.db_client.find_one('executor_summaries', {'_id' : executor_id, 'running' : running})

    def set_framework_summary_status_inactive(self, framework_id):
        try:
            self.logger.debug('Setting active state for framework id %s in database to false' % framework_id)
            framework_summary = {}
            framework_summary['active'] = False
            self.db_client.update('framework_summaries',
                {'_id' : framework_id},
                {'$set' : framework_summary}, upsert=True)
        except Exception, ex:
            self.logger.error('Cannot set status to false in framework summary: %s', ex)
            self.logger.debug('Troubled inactive framework: %s', framework_id)
            self.db_client.set_active(False)

        try:
            self.logger.debug('Setting active state for framework id %s for dependent tasks in database to false' % framework_id)
            task_summary = {}
            task_summary["active"] = False
            self.db_client.update('task_summaries',
                    {'framework_id' : framework_id},
                    {'$set' : task_summary}, upsert=True)
        except Exception, ex:
            self.logger.error('Cannot set status to false in task summary: %s', ex)
            self.logger.debug('Troubled inactive framework: %s', framework_id)
            self.db_client.set_active(False)

        try:
            self.logger.debug('Setting active state for framework id %s for dependent executors in database to false' % framework_id)
            executor_summary = {}
            executor_summary['running'] = False
            self.db_client.update('executor_summaries',
                    {'framework_id' : framework_id},
                    {'$set' : executor_summary}, upsert=True)
        except Exception, ex:
            self.logger.error('Cannot set status to false in executor summary: %s', ex)
            self.logger.debug('Troubled inactive framework: %s', framework_id)
            self.db_client.set_active(False)
            

    def update_framework_summary(self, framework_id, db_framework):
        self.logger.debug("Updating framework summary for %s" % framework_id)
        ft = FrameworkTracker.get_instance()
        framework = ft.get_active_or_finished_framework(framework_id)
        if framework is None:
            return
        framework_finished = ft.is_framework_finished(framework_id)
        framework_summary = {}
        framework_summary['_id'] = framework_id
        framework_summary['name'] = framework['name']
        framework_summary['user'] = framework['user']
        framework_summary['active'] = (not framework_finished)
        self.logger.trace("Framework finished %s" % framework_finished)

        # Update tasks, calculate resources
        task_summary = {}
        active_tasks = []
        tasks = db_framework.get('tasks', {})
        total_cpu = 0
        total_mem = 0
        executor_name = ''
        executor_dict = {}
        for (task_id, task) in tasks.items():
            task_info = task['task_info']
            task_summary['_id'] = "%s-%s" % (framework_id, task_id)
            task_summary['framework_id'] = framework_id
            task_summary['user'] = framework['user']
            task_summary['name'] = task_info.get('name', '')
            task_summary['started'] = task.get('start_time', '')
            task_summary['stopped'] = task.get('end_time', '')

            task_state = task.get('state', '')
            if framework_finished and task_state == "":
                task_summary['state'] = 'TASK_FINISHED'
            else:
                task_summary['state'] = task_state
            task_summary['active'] = (task_state == 'TASK_RUNNING' or task_state == 'TASK_STAGING') and not framework_finished
            self.logger.trace("Task summary: %s" % task_summary)

            slaves = db_framework.get('slaves', {})
            slave_id = task_info['slave_id']['value'] if 'slave_id' in task_info else task_info['agent_id']['value'] if 'agent_id' in task_info else "unknown"
            # slave id in dictionary has '.' replaced by '_'
            slave_id = slave_id.replace('.', '_')  
            slave = slaves.get(slave_id, {})
            executor_id = 'executor-%s' % slave_id

            # Get existing executor summary if needed
            # Assume no active tasks
            executor_running = True
            if not executor_dict.has_key(executor_id):
                try:
                    db_executor_summary = self.find_executor_summary(executor_id)
                    if db_executor_summary is not None:
                        executor_running = db_executor_summary['running']
                        if db_executor_summary['running'] == True:
                            self.logger.trace("Executor summary from db: %s" % db_executor_summary)
                            db_executor_summary['active_task'] = 0
                            db_executor_summary['cpu_alloc'] = 0
                            db_executor_summary['mem_alloc'] = 0
                            executor_dict[executor_id] = db_executor_summary
                    else:
                        self.logger.trace("Could not find executor summary for %s" % executor_id)
                except Exception, ex:
                    self.logger.error('Cannot find executor summary %s: %s', (executor_id, ex))
                    self.db_client.set_active(False)
                    return

            if task_state == 'TASK_RUNNING':
                active_tasks.append(task)
                resources = task_info.get('resources', [])
                task_cpu = 0
                task_mem = 0
                job_id = task.get('job_id')
                for resource in resources:
                    if resource.get('name') == 'cpus':
                        task_cpu = resource['scalar']['value']
                        total_cpu += task_cpu
                    elif resource.get('name') == 'mem':
                        task_mem = resource['scalar']['value']
                        total_mem += task_mem
                task_host = slave.get('hostname', '')

                if executor_running == True:
                    if task_info.get('executor'):
                        executor = task_info['executor']
                    else:
                        executor = {'name':'command executor','source':'command executor'}
                    executor_name = executor.get('name','NA')
                    if executor_dict.has_key(executor_id):
                        executor_summary = executor_dict.get(executor_id)
                        self.logger.trace("Current executor summary: %s" % executor_summary)
                    else:
                        executor_summary = {}
                        executor_summary['_id'] = executor_id
                        executor_summary['framework_id'] = framework_id
                        executor_summary['user'] = framework['user']
                        executor_summary['started'] = time.time()
                        executor_summary['name'] = executor_name
                        executor_summary['source'] = executor.get('source','NA')
                        executor_summary['running'] = True
                        executor_summary['cpu_alloc'] = 0
                        executor_summary['mem_alloc'] = 0
                        executor_dict[executor_id] = executor_summary
                        self.logger.trace("Executor summary initialized to: %s" % executor_summary)

                    executor_cpu_used = executor_summary.get('cpu_used', '')
                    if not executor_cpu_used:
                        executor_resource_usage = self.analyze_job_status_for_host(job_id, task_host)
                        executor_summary['cpu_used'] = executor_resource_usage.get('cpu_average', '')
                        executor_summary['mem_used'] = executor_resource_usage.get('mem_average', '')

                    executor_active_task = executor_summary.get('active_task', 0)
                    executor_active_task += 1
                    executor_summary['active_task'] = executor_active_task

                    executor_cpu_alloc = executor_summary.get('cpu_alloc', 0)
                    executor_cpu_alloc += task_cpu
                    executor_summary['cpu_alloc'] = executor_cpu_alloc

                    executor_mem_alloc = executor_summary.get('mem_alloc', 0)
                    executor_mem_alloc += task_mem
                    executor_summary['mem_alloc'] = executor_mem_alloc
                    self.logger.trace("Final executor summary: %s" % executor_summary)

                task_summary['host'] = task_host
            elif task_state == 'TASK_FINISHED' or task_state == 'TASK_FAILED' or task_state == 'TASK_KILLED':
                if executor_dict.has_key(executor_id):
                    self.logger.trace("Set executor summary running status to False for %s" % executor_id)
                    executor_summary = executor_dict.get(executor_id)
                    executor_summary['running'] = False
                else:
                    self.logger.trace("Not in dictionary for %s, set running status to False" % executor_id)
                    executor_summary = {}
                    executor_summary['_id'] = executor_id
                    executor_summary['running'] = False

            try:
                #self.logger.debug('Updating summary for task id %s' % task_id)
                id = task_summary['_id']
                del task_summary['_id']
                self.db_client.update('task_summaries',
                    {'_id' : id},
                    {'$set' : task_summary}, upsert=True)
            except Exception, ex:
                self.logger.error('Cannot store task summary: %s', ex)
                self.logger.debug('Troubled task: %s', task)
                self.db_client.set_active(False)

        # Update executor summaries
        for (executor_id, executor_summary) in executor_dict.items():
            self.update_executor_summary(executor_summary)

        # Update framework summary
        framework_summary['active_task'] = len(active_tasks)
        framework_summary['cpu'] = total_cpu
        framework_summary['mem'] = total_mem
        framework_summary['registered'] = db_framework.get('registered_time', '')
        framework_summary['reregistered'] = db_framework.get('reregistered_time', '')
        framework_summary['unregistered'] = db_framework.get('unregistered_time', '')
        framework_summary['executor'] = executor_name
        self.logger.trace("Framework summary: %s" % framework_summary)

        try:
            self.logger.debug('Updating summary for framework id %s in database' % framework_id)
            # Some mongo versions can't have the _id field in an update record...
            del framework_summary['_id']
            self.db_client.update('framework_summaries',
                {'_id' : framework_id},
                {'$set' : framework_summary}, upsert=True)
        except Exception, ex:
            self.logger.error('Cannot store framework summary: %s', ex)
            self.logger.debug('Troubled framework: %s', framework)
            self.db_client.set_active(False)

    def update_framework(self, framework_id):
        self.logger.debug('Updating framework id %s:' % framework_id)
        framework = FrameworkTracker.get_instance().get_active_or_finished_framework(framework_id)
        if framework is None:
            self.logger.debug('No framework for framework id %s:' % framework_id)
            return
#        td = framework.get('task_dict',{})
        self.logger.trace(framework)

        # Get existing framework
        try:
            db_framework = self.find_framework(framework_id)
            if db_framework is None:
                db_framework = {}
            self.logger.trace('Existing DB framework id %s: %s' % (framework_id, db_framework))
        except Exception, ex:
            self.logger.error('Cannot find framework %s: %s', (framework_id, ex))
            self.db_client.set_active(False)
            return

        # Filter out the 'unstorable' items from the framework
        filter_keys = ['channel','slave_dict','task_dict','lock','lock_acquired', 'offer_event']
        filtered_dict = dict((k,v) for k, v in framework.items() if not k.startswith('__') and k not in filter_keys)
        # job id is stored as set, which mongo can't handle
        original_job_id = filtered_dict.get('job_id')
        if original_job_id is not None:
            filtered_dict['job_id'] = list(original_job_id)
        if 'channel' in framework:
            filtered_dict['channel'] = framework['channel'].name

        # Special handling for slaves
        slave_dict = {} 
        for k1,v1 in framework.get('slave_dict',{}).items():
            for k2,v2 in v1.items():
                if k2 in ['channel','executor_channel']:
                    d = {k2: v2.name}
#                    self.logger.debug("1:d=%s" % d)
                elif k2 == 'command_executors':
#                    self.logger.debug("v2=%s" % v2)
                    dd = {}
                    for k3,v3 in v2.items():
#                        self.logger.debug("v3=%s" % v3)
                        for k4,v4 in v3.items():
                            if k4 == 'channel':
                                ddd = {k4: v4.name}
#                                self.logger.debug("1:ddd=%s" % ddd)
                            else:
                                ddd = {k4: v4}
#                                self.logger.debug("2:ddd=%s" % ddd)
                            dd[k3] = ddd
#                            self.logger.debug("2:dd=%s" % dd)
                    d = {k2: dd}
#                    self.logger.debug("2:d=%s" % d)
                else:
                    d = {k2: v2}
#                    self.logger.debug("3:d=%s" % d)
            replaced_key = k1.replace('.','_')
            slave_dict[replaced_key] = d

        # Special handling for tasks
        task_dict = {}
        for k,v in framework.get('task_dict',{}).items():
            replaced_key = k.replace('.','_')
            task_dict[replaced_key] = v

        # Get slaves/tasks from the existing db_framework and merge with
        # new ones. 
        db_slave_dict = db_framework.get('slaves', {}) # get old dict
        db_slave_dict.update(slave_dict)               # merge old with new dict
        db_framework['slaves'] = db_slave_dict         # replace old with new

        db_task_dict = db_framework.get('tasks', {})   # get old dict
        db_task_dict.update(task_dict)                 # merge old with new dict
        db_framework['tasks'] = db_task_dict           # replace old with new

        # We also need to check if our active framework is missing a registered time but we have one in the db
        if not framework.has_key("registered_time"):
            framework['registered_time'] = db_framework.get('registered_time',"")

        # Now merge db_framework with new filtered framework
        db_framework.update(filtered_dict)
        self.logger.trace('New DB framework id %s: %s' % (framework_id, db_framework))

        try:
            if db_framework.has_key('_id'):
                del db_framework['_id']
            self.db_client.update('frameworks',
                {'_id' : framework_id},
                {'$set' : db_framework}, upsert=True)
        except Exception, ex:
            self.logger.error('Cannot store framework: %s', ex)
            self.logger.debug('Troubled framework: %s',framework)
            self.db_client.set_active(False)

        # Update summary
        self.update_framework_summary(framework_id, db_framework)

    def update_executor_summary(self, executor_summary):
        try:
            self.logger.debug('Updating executor summary: %s' % (executor_summary))
            id = executor_summary['_id']
            del executor_summary['_id']
            self.db_client.update('executor_summaries',
                {'_id' : id},
                {'$set' : executor_summary}, upsert=True)
        except Exception, ex:
            self.logger.error('Cannot store executor summary: %s', ex)
            self.logger.debug('Troubled executor summary: %s', executor_summary)
            self.db_client.set_active(False)

    def update_offer_summary(self, offer):
        offer_summary = {}
        offer_summary['_id'] = offer['id']['value']
        offer_summary['framework_id'] = offer['framework_id']['value']
        offer_summary['host'] = offer['hostname']
        offer_summary['timestamp'] = time.time()
        for resource in  offer['resources']:
            if resource['name'] == 'mem':
                offer_summary['mem'] = resource['scalar']['value']
            elif resource['name'] == 'cpus':
                offer_summary['cpu'] = resource['scalar']['value']

        try:
            self.logger.debug('Updating offer summary: %s' % (offer_summary))
            id = offer_summary['_id']
            del offer_summary['_id']
            self.db_client.update('offer_summaries',
                {'_id' : id},
                {'$set' : offer_summary}, upsert=True)
        except Exception, ex:
            self.logger.error('Cannot store offer summary: %s', ex)
            self.logger.debug('Troubled offer: %s', offer)
            self.db_client.set_active(False)

    def analyze_job_status_for_host(self, job_id, host):
        self.logger.debug("Analyzing job status for job %s on host %s" % (job_id, host))
        if job_id is None:
            self.logger.debug("no job id")
            return {}
        job_info = JobTracker.get_instance().get(job_id)
        if job_info is None:
            self.logger.debug("no job info")
            return {}
        job_status = job_info.get('job_status')
        if job_status is None:
            self.logger.debug("no job status")
            return {}

        try:
            djob_info = job_status.get('detailed_job_info').get('djob_info').get('element')
            self.logger.trace("djob_info=%s" % djob_info)
            is_array = djob_info.get('JB_is_array')
#            tasks = djob_info.get('JB_ja_tasks').get('ulong_sublist')
#            if is_array == 'false':
#                tasks = [tasks]
            if is_array == 'true':
                tasks = djob_info.get('JB_ja_tasks').get('ulong_sublist')
                if tasks is None:
                    self.logger.debug("no tasks in array job")
                    return {}
            else:
                task = djob_info.get('JB_ja_tasks').get('element')
                if task is None:
                    self.logger.debug("no tasks")
                    return {}   
                tasks = [ task ]

            self.logger.trace("tasks=%s" % tasks)
            now = time.time()
            cpu_average = 0
            mem_average = 0
            for t in tasks:
                if t is None:
                    self.logger.trace("Task is None, continue task loop")
                    continue
                start_time = float(t.get('JAT_start_time'))/1000.
                delta_t = now - start_time
                self.logger.trace("start_time=%s, now=%s, delta=%s" % (start_time, now, delta_t))
                task_number = t.get('JAT_task_number')
                scaled_usage_list = t.get('JAT_scaled_usage_list')
                if scaled_usage_list is None:
                    self.logger.trace("scaled_usage_list is None, continue task loop")
                    continue
                usage_list = scaled_usage_list.get('scaled')
                if usage_list == None:
                    usage_list = scaled_usage_list.get('Events')
                    if usage_list == None:
                        self.logger.trace("No scaled or Events in scaled_usage_list, continue task loop")
                        continue
                        
                self.logger.trace("usage_list=%s" % usage_list)
                identifier_list = t.get('JAT_granted_destin_identifier_list').get('element')
                task_host = identifier_list.get('JG_qhostname')
                # Only analyze tasks on a given host
                if task_host != host:
                    self.logger.trace("task_host=%s (not %s), continue task loop" % (task_host, host))
                    continue
                for u in usage_list:
                    u_name = u.get('UA_name')
                    if u_name == 'cpu':
                        u_value = float(u.get('UA_value'))
                        # value is integrated cpu seconds, so divide by time
                        # to get average cpu used
                        task_cpu_average = u_value/delta_t
                        cpu_average += task_cpu_average
                        self.logger.trace("u_value=%s, task_cpu_average=%s, cpu_average=%s" % (u_value, task_cpu_average, cpu_average))
                    elif u_name == 'mem':
                        # value is integrated GB seconds, so divide by time
                        # to get average GB used
                        u_value = float(u.get('UA_value'))*1024.
                        task_mem_average = u_value/delta_t
                        mem_average += task_mem_average
                        self.logger.trace("u_value=%s, task_mem_average=%s, mem_average=%s" % (u_value, task_mem_average, mem_average))
            self.logger.trace("cpu_average=%s, mem_average=%s" % (cpu_average, mem_average))
            return {'cpu_average' : cpu_average, 'mem_average' : mem_average}
        except Exception, ex:
            self.logger.warn('Could not analyze job %s on host %s (tasks=%s): %s' % (job_id, host, tasks, ex))
        return {}

    def update_completed_executor_summary(self, executor_id):
        # Get existing executor summary if needed
        # Assume no active tasks
        executor_id = executor_id.replace('.', '_')
        try:
            db_executor_summary = self.find_executor_summary(executor_id, True)
            if db_executor_summary is not None:
                self.logger.debug('Marking executor %s as done in db' % executor_id)
                db_executor_summary['active_task'] = 0
                db_executor_summary['running'] = False
                db_executor_summary['stopped'] = time.time()
                self.update_executor_summary(db_executor_summary)
            else:
                self.logger.debug('Could not find executor %s to mark as done in db' % executor_id)
        except Exception, ex:
            self.logger.error('Cannot find executor summary %s: %s', (executor_id, ex))
            self.db_client.set_active(False)

    def is_active(self):
        return self.db_client.is_active()
