#!/usr/bin/env python

# Copyright 2018 Univa Corporation
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


import json
import datetime
import time
import os
import sys
import threading
import logging
import signal
import sys
import uuid
import getpass
from mesoshttp.client import MesosClient


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


    def __init__(self, url="http://127.0.0.1:5050"):
        logging.basicConfig()
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.launched_tasks = 0
        self.running_tasks = 0
        self.finished_tasks = 0
        self.killed_tasks = 0
        self.lost_tasks = []
#        self.failed_tasks = []
        #signal.signal(signal.SIGINT, signal.SIG_IGN)
        logging.getLogger('mesoshttp').setLevel(logging.DEBUG)
        self.driver = None
        self.client = MesosClient(mesos_urls=[url], frameworkId=None, frameworkName='Python HTTP framework', frameworkUser=getpass.getuser())
        self.client.on(MesosClient.SUBSCRIBED, self.subscribed)
        self.client.on(MesosClient.OFFERS, self.offer_received)
        self.client.on(MesosClient.UPDATE, self.status_update)
        self.th = Test.MesosFramework(self.client)
        self.th.start()
        while True and self.th.isAlive():
            try:
                self.th.join(1)
            except KeyboardInterrupt:
                self.shutdown()
                break


    def shutdown(self):
        print('Stop requested by user, stopping framework....')
        self.logger.info('Stop requested by user, stopping framework....')
        self.driver.tearDown()
        self.client.stop = True
        self.stop = True


    def subscribed(self, driver):
        self.logger.info('SUBSCRIBED')
        self.driver = driver

    def status_update(self, update):
        status = update['status']['state']
        task = update['status']['task_id']['value']
        self.logger.info("Task %s: %s" % (task, status))
        if status == 'TASK_RUNNING':
            self.running_tasks+=1
            if not self.running_tasks%3:
#            if not self.running_tasks%3 and task not in self.failed_tasks:
                self.logger.info("Killing task: %s" % task)
                self.driver.kill(update['status']['agent_id']['value'], task)
        elif status == 'TASK_FINISHED':
            self.finished_tasks+=1
            if self.finished_tasks >= max_tasks:
                self.logger.info("All %d tasks finished, shutdown now" % self.finished_tasks)
                self.shutdown()
        elif status == 'TASK_LOST':
#            self.lost_tasks.append(task)
            self.logger.info("Reconcile on lost task")
            self.driver.reconcile([])
        elif status == 'TASK_FAILED':
            self.failed_tasks.append(task)
            self.logger.info("Reconcile on failed task")
            self.driver.reconcile([])
        else:
            self.logger.info("Status update: %s" % update['status']['state'])
        self.logger.info("(l%d/f%d/r%d/m%d)" % (self.launched_tasks, self.finished_tasks, self.running_tasks, max_tasks))

    def offer_received(self, offers):
        self.logger.info('OFFER: %s' % (str(offers)))
        i = 0
        if len(self.lost_tasks) > 0:
            task_name = self.lost_tasks.pop(0)
            print("Relaunching lost task: %s" % task_name)
        else:
            task_name = uuid.uuid4().hex
            
        for offer in offers:
            if i == 0:
                self.run_job(offer, task_name)
            else:
                offer.decline()
            i+=1

#    def run_job(self, mesos_offer, task_name = uuid.uuid4().hex):
    def run_job(self, mesos_offer, task_name):
        offer = mesos_offer.get_offer()
        cmd = "sleep 3" if self.launched_tasks%4 else 'sleep 2; exit 1'
#        print(str(offer))
        task = {
            'name': 'sample test',
            'task_id': {'value': task_name},
            'agent_id': {'value': offer['agent_id']['value']},
            'resources': [
            {
                'name': 'cpus',
                'type': 'SCALAR',
                'scalar': {'value': 0.1}
            },
            {
                'name': 'mem',
                'type': 'SCALAR',
                'scalar': {'value': 100}
            }
            ],
            'command': {'value': cmd},
        }

        mesos_offer.accept([task])
        self.launched_tasks+=1

url = "http://127.0.0.1:5050" if len(sys.argv) == 1 else sys.argv[1]
max_tasks = int(sys.argv[2]) if len(sys.argv) == 3 else 5

test_mesos = Test(url)
