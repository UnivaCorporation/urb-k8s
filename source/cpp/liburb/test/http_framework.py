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
        self.launched_tasks = 0
        self.running_tasks = 0
        self.finished_tasks = 0
        self.killed_tasks = 0
        self.lost_tasks = []
        #signal.signal(signal.SIGINT, signal.SIG_IGN)
        logging.getLogger('mesoshttp').setLevel(logging.INFO)
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
        if update['status']['state'] == 'TASK_RUNNING':
            self.running_tasks+=1
            self.logger.info("Task %s (%d/%d/%d): TASK_RUNNING" % (update['status']['task_id']['value'], self.launched_tasks, self.running_tasks, max_tasks))
            if self.running_tasks%2:
                self.logger.info("Killing task: %s" % update['status']['task_id']['value'])
                self.driver.kill(update['status']['agent_id']['value'], update['status']['task_id']['value'])
        elif update['status']['state'] == 'TASK_FINISHED':
            self.logger.info("Task %s (%d/%d/%d): TASK_FINISHED" % (update['status']['task_id']['value'], self.launched_tasks, self.finished_tasks, max_tasks))
            self.finished_tasks+=1
            if self.finished_tasks >= max_tasks:
                self.logger.info("All %d tasks finished, shutdown now" % self.finished_tasks)
                self.shutdown()
        elif update['status']['state'] == 'TASK_KILLED':
            self.logger.info("Task %s: TASK_KILLED" % update['status']['task_id']['value'])
        elif update['status']['state'] == 'TASK_FAILED':
            self.logger.info("Task %s: TASK_FAILED" % update['status']['task_id']['value'])
        elif update['status']['state'] == 'TASK_LOST':
            self.logger.info("Task %s: TASK_LOST" % update['status']['task_id']['value'])
            self.lost_tasks.append(update['status']['task_id']['value'])
        else:
            self.logger.info("Status update: %s" % update['status']['state'])

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
        cmd = "sleep 3" if self.launched_tasks%3 else 'sleep 2; exit 1'
#        print(str(offer))
        task = {
            'name': 'sample test',
            'task_id': {'value': task_name},
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
            'command': {'value': cmd},
        }

        mesos_offer.accept([task])
        self.launched_tasks+=1

url = "http://127.0.0.1:5050" if len(sys.argv) == 1 else sys.argv[1]
max_tasks = int(sys.argv[2]) if len(sys.argv) == 3 else 5

test_mesos = Test(url)
