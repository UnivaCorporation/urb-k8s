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
import copy

# add path to test util
sys.path.append('../../urb-core/source/python/test')
# add path to urb
sys.path.append('../../urb-core/source/python')

from common_utils import needs_setup
from common_utils import needs_cleanup
from common_utils import create_service_thread
from common_utils import create_service_channel
from common_utils import need_python_27

from urb.config.config_manager import ConfigManager

from mesoshttp.client import MesosClient

if os.environ.get("URB_CONFIG_FILE") is None:
    raise Exception("URB_CONFIG_FILE environment variable has to be defined")

from gevent import monkey
monkey.patch_all()

SERVICE_THREAD = create_service_thread(serve_time=100)

CM = ConfigManager.get_instance()
HTTP_PORT = CM.get_config_option("Http", "scheduler_port", "5060")
URL = "http://127.0.0.1:" + HTTP_PORT

class Test(object):
    class MesosFramework(threading.Thread):
        def __init__(self, client):
            threading.Thread.__init__(self)
            self.client = client
            self.exited = False

        def run(self):
            try:
                self.client.register()
            except KeyboardInterrupt:
                print('Stop requested by user, stopping framework....')
            print("MesosFramework: run end")
            self.exited = True

        def is_done(self):
            return self.exited

    def __init__(self, url="http://127.0.0.1:5050", name="HTTP framework", user="vagrant"):
        logging.basicConfig()
        self.logger = logging.getLogger(__name__)
        self.tasks = 0
        #signal.signal(signal.SIGINT, signal.SIG_IGN)
        logging.getLogger('mesoshttp').setLevel(logging.DEBUG)
        self.driver = None
        self.mesos_offer = None # to store only one offer
        self.update = None
        self.task_id = None
        self.agent_id = None
        self.client = MesosClient(mesos_urls = [url], frameworkName = name, frameworkUser = user)
        self.client.on(MesosClient.SUBSCRIBED, self.subscribed)
        self.client.on(MesosClient.OFFERS, self.offer_received)
        self.client.on(MesosClient.UPDATE, self.status_update)
        self.th = Test.MesosFramework(self.client)

    def reset_offer(self):
        ret = copy.deepcopy(self.mesos_offer)
        self.mesos_offer = None
        return ret

    def reset_update(self):
        ret = copy.deepcopy(self.update)
        self.update = None
        return ret

    def start(self):
        self.th.start()

    def is_done(self):
        return self.th.is_done()

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

    def subscribed(self, driver):
        print('SUBSCRIBED')
        self.driver = driver

    def status_update(self, update):
        print("STATUS UPDATE: %s" % update['status']['state'])
        if self.update is None:
            self.update = update
            self.task_id = update['status']['task_id']
            self.agent_id = update['status']['agent_id']
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

    def run_task(self, sec, o = None):
        offer = o if o else self.mesos_offer.get_offer()
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

    def kill_task(self, task_name = None, agent_name = None):
        t = task_name if task_name else self.update['status']['task_id']['value']
        a = agent_name if agent_name else self.update['status']['agent_id']['value']
        print("kill task: %s on %s" % (t, a))
        self.driver.kill(a, t)

    def send_message(self, msg, agent_id = None, executor_id = None):
        a = agent_id if agent_id else self.update['agent_id']
        e = task_name if task_name else self.update['executor_id']
        print("Send message: %s" % msg)
        self.driver.message(a, e, msg)

    def reconcile(self):
        print("Reconcile")
        task = { 'task_id' : self.task_id, 'agent_id' : self.agent_id }
        self.driver.reconcile([task])


URB_TEST = Test(URL)

@needs_setup
@need_python_27
def test_setup():
    print 'HTTP Test Starting service thread'
    SERVICE_THREAD.start()
    gevent.sleep(3)

@need_python_27
def test_subscribe():
    gevent.sleep(3)
    print 'HTTP Test Subscribe'
    URB_TEST.start()
    print("HTTP Test Subscribe, started, URB_TEST=%s" % repr(URB_TEST))
    gevent.sleep(2)

@need_python_27
def test_launch_long_task():
    print("HTTP Test Launch long task")
    print("URB_TEST=%s" % repr(URB_TEST))
    assert URB_TEST.wait_offer(15)
    URB_TEST.run_task(30)

@need_python_27
def test_status_update_long_task():
    print("HTTP Test Status update long task")
    update = URB_TEST.wait_update(15)
    assert update
    assert update['status']['state'] == 'TASK_LOST'
#    assert update['status']['state'] == 'TASK_RUNNING'

@need_python_27
def test_reconcile_long_task():
    print("HTTP Test reconcile")
    URB_TEST.reset_update()
    URB_TEST.reconcile()
    update = URB_TEST.wait_update(15)
    assert update
    assert (update['status']['state'] == 'TASK_LOST' and update['status']['reason'] == 'REASON_RECONCILIATION')
#    assert (update['status']['state'] == 'TASK_RUNNING' and update['status']['reason'] == 'REASON_RECONCILIATION')

#def test_message():
#    print("HTTP Test message long task")
#    URB_TEST.send_message("message")

@need_python_27
def test_kill_long_task():
    print("HTTP Test Kill long task")
    update = URB_TEST.reset_update()
    URB_TEST.kill_task(update['status']['task_id']['value'], update['status']['agent_id']['value'])
    update = URB_TEST.wait_update(15)
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
@need_python_27
def test_cleanup():
    print("HTTP Test cleanup")
    URB_TEST.shutdown()
    print("Sent shutdown test framework")
    for i in range(10):
        if URB_TEST.is_done():
            break
        gevent.sleep(2)
        print("waiting for framework shutdown... %d" % i)
    # Try and signal a shutdown but just wait for the timeout if it fails
    try:
        from urb.service.urb_service_controller import URBServiceController
        from gevent import monkey; monkey.patch_socket()
        controller = URBServiceController('urb.service.monitor')
        print("Shutdown URB service")
        controller.send_shutdown_message()
    except:
        print("Exception, pass")
        pass
    print("Joining service thread")
    SERVICE_THREAD.join()
    print("HTTP Test cleanup, done")


# Testing
if __name__ == '__main__':
#    test_env()
    test_setup()
    test_subscribe()
    test_launch_long_task()
    test_status_update_long_task()
    test_reconcile_long_task()
    test_kill_long_task()
    print("END")
    test_cleanup()
    pass
