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


import socket
import gevent
import os
import sys
# add path to test util
sys.path.append('../../urb-core/source/python/test')
# add path to urb
sys.path.append('../../urb-core/source/python')
from k8s_adapter.k8s_adapter import K8SAdapter
from urb.messaging.channel_factory import ChannelFactory
from urb.config.config_manager import ConfigManager
from urb.utility.framework_tracker import FrameworkTracker
from urb.exceptions.urb_exception import URBException
from urb.exceptions.unknown_job import UnknownJob
from urb.exceptions.completed_job import CompletedJob
from kubernetes import client, config
from kubernetes.client.rest import ApiException

os.environ["URB_CONFIG_FILE"] = os.path.dirname(os.path.realpath(__file__)) + "/urb.conf"
client.Configuration().host="http://127.0.0.1:8001"
#client.Configuration().host="http://192.168.99.100:8433"

#@needs_uge
def test_short_job_management():
    adapter = K8SAdapter()
    adapter.set_command(["/bin/sh", "-c", "env; sleep 1"])
    print("Submitting short jobs")
    jobs_num = 1
    job_ids = adapter.submit_jobs(100, jobs_num, {'URB_FRAMEWORK_ID': 'framework-1', 'URB_FRAMEWORK_NAME':'test'})
    print("Got job ids: %s" % job_ids)
    assert job_ids != None
    gevent.sleep(3)
    for jid in job_ids:
        try:
            adapter.get_job_status(jid[0])
        except CompletedJob as e:
            print("Job status: completed")
        gevent.spawn(adapter.delete_job, jid[0])
    gevent.sleep(2)
    for jid in job_ids:
        try:
            print("Get status of the finished job: %s" % jid[0])
            adapter.get_job_status(jid[0])
            assert False
        except ApiException as e:
            if e.reason == "Not Found":
                pass
            else:
                assert False
        except CompletedJob as e:
            pass

def test_long_job_management():
    adapter = K8SAdapter()
    adapter.set_command(["/bin/sh", "-c", "env; sleep 100"])
    print("Submitting long jobs")
    jobs_num = 1
    job_ids = adapter.submit_jobs(100, jobs_num, {'URB_FRAMEWORK_ID': 'framework-1', 'URB_FRAMEWORK_NAME':'test'})
    print("Got job ids: %s" % job_ids)
    assert job_ids != None
    gevent.sleep(1)
    for jid in job_ids:
        print("Job status: %s" % adapter.get_job_status(jid[0]))
        gevent.spawn(adapter.delete_job, jid[0])
    gevent.sleep(3)
    for jid in job_ids:
        try:
            print("Get status of the deleted job: %s" % jid[0])
            adapter.get_job_status(jid[0])
            assert False
        except ApiException as e:
            if e.reason == "Not Found":
                pass
            else:
                assert False

def test_register_framework():
    print("Registering framework")
    cm = ConfigManager.get_instance()
    cf = ChannelFactory.get_instance()
    framework_env = {
        'URB_CONFIG_FILE' : cm.get_config_file(),
        'URB_FRAMEWORK_ID' : '1',
        'URB_FRAMEWORK_NAME':'test',
        'URB_MASTER' : cf.get_message_broker_connection_url(),
    }
    adapter = K8SAdapter()
    adapter.set_command(["/bin/sh", "-c", "env; sleep 100"])
    max_tasks = 5
    concurrent_tasks = 1
    # specify unused parameters
    kwargs = {'class': 'class',
              'submit_options': 'submit_options'};
    job_ids = adapter.register_framework(max_tasks, concurrent_tasks, framework_env, **kwargs)
    print 'JOB IDs: ', job_ids
    framework = {
        'job_ids' : job_ids,
        'name' : 'framework_name',
        'id' : {'value' : 1},
        'config' : {'mem' : 1024, 'disk' : 16384, 'cpus' : 1, 
                    'ports' : '[(30000,31000)]',
                    'max_rejected_offers' : 1,
                    'max_tasks' : 5
        }
    }
    FrameworkTracker.get_instance().add(1, framework)
    assert job_ids != None

def test_unregister_framework():
    framework = FrameworkTracker.get_instance().get(1)
    print("Unregistering framework: %s" % framework)
    framework_name = framework.get('name')
    job_ids = framework.get('job_ids')
    assert job_ids != None
    j_list = list(job_ids)
    adapter = K8SAdapter()
    adapter.unregister_framework(framework)
    gevent.sleep(3)
    for i in range(0,12):
        j_del = []
        print("Job list: %s" % j_list)
        for job_id in j_list:
            try:
                jid = job_id[0]
                print("Get job status for: %s" % jid)
                resp = adapter.get_job_status(jid)
                print("Status: %s" % resp.status)
            except ApiException as e:
                if e.reason == "Not Found":
                    print("Was deleted")
                    j_del.append(job_id)
                    pass
        j_list = [x for x in j_list if x not in j_del]
        if len(j_list) == 0:
            break
        gevent.sleep(1)
    else:
        raise URBException("Jobs %s were not deleted" % j_list)
    print("Jobs %s were deleted" % job_ids)

# Testing
if __name__ == '__main__':
    pass
