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
import json
import sys
import os
import uuid
import logging
import threading

# add path to test util
sys.path.append('../../urb-core/source/python/test')
# add path to urb
sys.path.append('../../urb-core/source/python')

from common_utils import needs_setup
from common_utils import needs_cleanup
from common_utils import create_service_thread
from common_utils import create_service_channel

from urb.config.config_manager import ConfigManager

from mesoshttp.client import MesosClient

if os.environ.get("URB_CONFIG_FILE") is None:
    raise Exception("URB_CONFIG_FILE environment variable has to be defined")

#from gevent import monkey
#monkey.patch_all()

SERVICE_THREAD = create_service_thread(serve_time=100)

CM = ConfigManager.get_instance()
HTTP_PORT = CM.get_config_option("Http", "port", "5050")
URL = "http://127.0.0.1:" + HTTP_PORT

class Test(object):
    class MesosFramework(threading.Thread):
        def __init__(self, client):
            threading.Thread.__init__(self)
            self.client = client
            self.stop = False

        def run(self):
            try:
                self.client.register()
            except KeyboardInterrupt:
                print('Stop requested by user, stopping framework....')

    def __init__(self, url="http://127.0.0.1:5050", name="HTTP framework", user="vagrant"):
        logging.basicConfig()
        self.logger = logging.getLogger(__name__)
        self.tasks = 0
        #signal.signal(signal.SIGINT, signal.SIG_IGN)
        logging.getLogger('mesoshttp').setLevel(logging.DEBUG)
        self.driver = None
        self.mesos_offer = None # to store only one offer
        self.update = None
        self.client = MesosClient(mesos_urls = [url], frameworkName = name, frameworkUser = user)
        self.client.on(MesosClient.SUBSCRIBED, self.subscribed)
        self.client.on(MesosClient.OFFERS, self.offer_received)
        self.client.on(MesosClient.UPDATE, self.status_update)
        self.th = Test.MesosFramework(self.client)

    def reset_offer(self):
        mesos_offer = None

    def reset_update(self):
        self.update = None

    def start(self):
        self.th.start()

    def wait_offer(self, sec):
        cnt = 0
        while self.mesos_offer is None and cnt < sec:
            print("Waiting for offer: %d" % cnt)
            cnt += 1
            gevent.sleep(1)
        if self.mesos_offer is None:
            print("Timeout waiting for offer")
        return self.mesos_offer
#        return self.wait4(self.mesos_offer, sec, "offer")

    def wait_update(self, sec):
        cnt = 0
        while self.update is None and cnt < sec:
            print("Waiting for update %d" %  cnt)
            cnt += 1
            gevent.sleep(1)
        if self.update is None:
            print("Timeout waiting for update")
        return self.update
#        return self.wait4(self.update, sec, "update")

    def wait4(self, obj, sec, msg):
        cnt = 0
        while obj is None and cnt < sec:
            print("Waiting for %s %s %d" % (msg, repr(obj), cnt))
            cnt += 1
            gevent.sleep(1)
        if obj is None:
            print("Timeout waiting for: %s" % msg)
        return obj

    def shutdown(self):
        print('Stop requested by user, stopping framework....')
        self.driver.tearDown()
        self.client.stop = True
        self.stop = True

    def subscribed(self, driver):
        print('SUBSCRIBED')
        self.driver = driver

    def status_update(self, update):
        print("STATUS UPDATE: %s" % update['status']['state'])
        if self.update is None:
            self.update = update
            print("Use update: %s" % self.update)
#        if update['status']['state'] == 'TASK_RUNNING':
#            self.tasks+=1
#            self.logger.warn("Task %s (%d/%d): TASK_RUNNING" % (update['status']['agent_id']['value'],self.tasks,max_tasks))
#            self.driver.kill(update['status']['agent_id']['value'], update['status']['task_id']['value'])
#            if self.tasks >= max_tasks:
#                self.logger.warn("Max tasks %d lauched, shutdown now" % self.tasks)
#                self.shutdown()
#        elif update['status']['state'] == 'TASK_FINISHED':
#            self.logger.warn("Task %s: TASK_FINISHED" % update['status']['agent_id']['value'])
#            self.tasks+=1
#            if self.tasks >= self.max_tasks:
#                self.shutdown()
#        else:
#            self.logger.warn("Status update: %s" % update['status']['state'])

    def offer_received(self, offers):
        print("OFFERS: %s" % (str(offers)))
        i = 0
        for offer in offers:
            if i == 0 and self.mesos_offer is None:
                self.mesos_offer = offer
                print("Use offer: %s" % self.mesos_offer.get_offer())
            else:
                print("Declining offer: %s" % offer.get_offer())
                offer.decline()
            i+=1

    def run_task(self, sec):
        offer = self.mesos_offer.get_offer()
        print("Run task on offer: %s" % str(offer))
        task = {
            'name': 'sample test',
            'task_id': {'value': uuid.uuid4().hex},
            'agent_id': {'value': offer['agent_id']['value']},
            'resources': [
            {
                'name': 'cpus',
                'type': 'SCALAR',
                'scalar': {'value': 1}
            },
            {
                'name': 'mem',
                'type': 'SCALAR',
                'scalar': {'value': 1000}
            }
            ],
            'command': {'value': 'sleep ' + str(sec)},
        }
        self.mesos_offer.accept([task])

    def kill_task(self):
        print("kill task: %s on %s" % (self.update['status']['task_id']['value'], self.update['status']['agent_id']['value']))
        self.driver.kill(self.update['status']['agent_id']['value'], self.update['status']['task_id']['value'])

    def send_message(msg):
        print("Send message: %s" % msg)
        agent_id = self.update['agent_id']
        executor_id = self.update['executor_id']
        self.driver.message(agent_id, executor_id, msg)
        

URB_TEST = Test(URL)

@needs_setup
def test_setup():
    print 'HTTP Test Starting service thread'
    SERVICE_THREAD.start()
    gevent.sleep(3)

def test_subscribe():
    gevent.sleep(3)
    print 'HTTP Test Subscribe'
    URB_TEST.start()
    print("HTTP Test Subscribe, started, URB_TEST=%s" % repr(URB_TEST))
    gevent.sleep(2)

def test_launch_long_task():
    print("HTTP Test Launch long task")
    print("URB_TEST=%s" % repr(URB_TEST))
    assert URB_TEST.wait_offer(15)
    URB_TEST.run_task(30)

def test_status_update_long_task():
    print("HTTP Test Status update long task")
    update = URB_TEST.wait_update(15)
    assert update
    assert update['status']['state'] == 'TASK_LOST'
#    assert update['status']['state'] == 'TASK_RUNNING'

def test_reconcile_long_task():
    printt("HTTP Test reconcile")
    URB_TEST.reset_update()
    URB_TEST.reconcile()
    update = URB_TEST.wait_update(10)
    assert update
    assert (update['status']['state'] == 'TASK_RUNNING' and update['status']['reason'] == 'REASON_RECONCILIATION')

#def test_message():
#    print("HTTP Test message long task")
#    URB_TEST.send_message("message")

def test_kill_long_task():
    print("HTTP Test Kill long task")
    URB_TEST.kill_task()
    URB_TEST.reset_update()
    update = URB_TEST.wait_update(10)
    assert update
    assert update['status']['state'] == 'TASK_KILLED'

#def test_launch_short_task():
#    print("HTTP Test Launch short task")
#    URB_TEST.reset_offer()
#    assert URB_TEST.wait_offer(15)
#    URB_TEST.run_task(1)
    
#def test_status_update_short_task():
#    print("HTTP Test Status update short task")
#    gevent.sleep(2)
#    update = URB_TEST.wait_update(10)
#    assert update
#    assert update['status']['state'] == 'TASK_FINISHED'



@needs_cleanup
def test_cleanup():
    URB_TEST.shutdown()
    # Try and signal a shutdown but just wait for the timeout if it fails
    try:
        from urb.service.urb_service_controller import URBServiceController
        from gevent import monkey; monkey.patch_socket()
        controller = URBServiceController('urb.service.monitor')
        controller.send_shutdown_message()
    except:
        pass
    SERVICE_THREAD.join()

# Testing
if __name__ == '__main__':
#    test_env()
    test_setup()
    test_subscribe()
    test_launch_long_task()
    test_status_update_long_task()
#    test_reconcile_long_task()
#    test_kill_long_task()
#    print("Before sleep")
#    gevent.sleep(20)
#    print("After sleep")
    print("END")
    test_cleanup()
    pass
