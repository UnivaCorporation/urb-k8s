#!/usr/bin/env python

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import time

import mesos.interface
from mesos.interface import mesos_pb2
import mesos.native
import signal
import logging

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.DEBUG)
logger = logging.getLogger("test_framework")
logger.setLevel(logging.DEBUG)

TOTAL_TASKS = 50
TOTAL_TASKS_2ND = 0
TOTAL_TASKS_3RD = 0
TASK_CPUS = 1
TASK_MEM = 32

def handler(signum, frame):
    logger.info("Got signal %s" % signum)

class TestScheduler(mesos.interface.Scheduler):
  def __init__(self, implicitAcknowledgements, executor):
    self.implicitAcknowledgements = implicitAcknowledgements
    self.executor = executor
    self.reset()

  def reset(self):
    self.taskData = {}
    self.tasksLaunched = 0
    self.tasksFinished = 0
    self.messagesSent = 0
    self.messagesReceived = 0
    self.results = [ False for i in range(0,TOTAL_TASKS) ]
    self.messages = [ False for i in range(0,TOTAL_TASKS) ]
    self.lost_tasks = []
    self.done = False

  def registered(self, driver, frameworkId, masterInfo):
    logger.info("Registered with framework ID %s" % frameworkId.value)

  def __add_task(self, tasks, tid, offer):
     task = mesos_pb2.TaskInfo()
     task.task_id.value = str(tid)
     task.slave_id.value = offer.slave_id.value
     task.name = "task %d" % tid
     task.executor.MergeFrom(self.executor)

     cpus = task.resources.add()
     cpus.name = "cpus"
     cpus.type = mesos_pb2.Value.SCALAR
     cpus.scalar.value = TASK_CPUS

     mem = task.resources.add()
     mem.name = "mem"
     mem.type = mesos_pb2.Value.SCALAR
     mem.scalar.value = TASK_MEM

     tasks.append(task)
     self.taskData[task.task_id.value] = (
         offer.slave_id, task.executor.executor_id)

  def resourceOffers(self, driver, offers):
    logger.info("Got %d resource offers" % len(offers))
    for offer in offers:
      tasks = []
      logger.info("Got resource offer %s" % offer.id.value)
      if self.tasksLaunched < TOTAL_TASKS:
        tid = self.tasksLaunched
        self.tasksLaunched += 1

        logger.info("Accepting offer on %s to start task %d" % (offer.hostname, tid))
        self.__add_task(tasks,tid,offer)
      else:
          # Look for uncompleted tasks
          logger.info("Checking for uncompleted tasks")
          for i in range(0,TOTAL_TASKS):
              if not self.results[i]:
                  logger.info("\tTask %d has not completed" % i)
          # Look for lost messages
          logger.info("Checking for missing messages")
          for i in range(0,TOTAL_TASKS):
              if not self.messages[i]:
                  logger.info("\tMessage %d has not been received" % i)
          # Lets look for lost tasks
          if len(self.lost_tasks) > 0:
              logger.info("\thave %d lost task(s)." % len(self.lost_tasks))
              tid = self.lost_tasks.pop()
              logger.info("\tAccepting offer on %s to start lost task %s" % (offer.hostname, tid))
              self.__add_task(tasks,tid,offer)
      driver.launchTasks(offer.id, tasks)

  def statusUpdate(self, driver, update):
    logger.info("Task %s is in state %d" % (update.task_id.value, update.state))

    if  update.state == mesos_pb2.TASK_LOST:
        # Lost task... lets store this task id
        self.lost_tasks.append(int(update.task_id.value))
        return

    # Ensure the binary data came through.
    if update.data != "data with a \0 byte":
      logger.info("The update data did not match!")
      logger.info("  Expected: 'data with a \\x00 byte'")
      logger.info("  Actual: %s", repr(str(update.data)))
      sys.exit(1)

    if update.state == mesos_pb2.TASK_FINISHED:
      self.tasksFinished += 1
      if self.results[int(update.task_id.value)]:
          logger.info("DUP finished message for task: %s" % update.task_id.value)
      self.results[int(update.task_id.value)] = True
      if self.tasksFinished == TOTAL_TASKS:
        logger.info("All tasks done, waiting for final framework message")

      slave_id, executor_id = self.taskData[update.task_id.value]

      self.messagesSent += 1
      driver.sendFrameworkMessage(
          executor_id,
          slave_id,
          'task [%s] data with a \0 byte' % update.task_id.value)

      if update.state == mesos_pb2.TASK_LOST or \
         update.state == mesos_pb2.TASK_KILLED or \
         update.state == mesos_pb2.TASK_FAILED:
        logger.info("Aborting because task %s is in unexpected state %s with message '%s'" \
              % (update.task_id.value, mesos_pb2.TaskState.Name(update.state), update.message))
        driver.abort()

      # Explicitly acknowledge the update if implicit acknowledgements
      # are not being used.
      if not self.implicitAcknowledgements:
        driver.acknowledgeStatusUpdate(update)

  def frameworkMessage(self, driver, executorId, slaveId, message):
    self.messagesReceived += 1

    # The message bounced back as expected.
    if not message.endswith("data with a \0 byte"):
      logger.info("The returned message data did not match!")
      logger.info("  Expected: '.*data with a \\x00 byte'")
      logger.info("  Actual: %s" % repr(str(message)))
      sys.exit(1)
    logger.info("Received message (%d of %d): %s" % (self.messagesReceived, TOTAL_TASKS, repr(str(message))))

    task_id = int(message[message.find("[")+1:message.find("]")])
    if self.messages[task_id]:
        logger.info("DUP framework message for task: %s" % task_id)
    self.messages[task_id] = True
    if self.messagesReceived == TOTAL_TASKS:
      if self.messagesReceived != self.messagesSent:
        logger.info("Sent %d" % self.messagesSent,)
        logger.info("but received %d", self.messagesReceived)
        sys.exit(1)
      logger.info("All tasks done, and all messages received, exiting")
#      driver.stop()
      self.done = True

if __name__ == "__main__":
  argvlen = len(sys.argv)
  if argvlen < 2 or argvlen > 5:
    logger.info("Usage: %s master [tasks] [2nd_run_tasks] [3rd_run_tasks]" % sys.argv[0])
    sys.exit(1)

  if argvlen == 3:
    TOTAL_TASKS = int(sys.argv[2])
  elif argvlen == 4:
    TOTAL_TASKS = int(sys.argv[2])
    TOTAL_TASKS_2ND = int(sys.argv[3])
  elif argvlen == 5:
    TOTAL_TASKS = int(sys.argv[2])
    TOTAL_TASKS_2ND = int(sys.argv[3])
    TOTAL_TASKS_3RD = int(sys.argv[4])

  executor = mesos_pb2.ExecutorInfo()
  executor.executor_id.value = "default"
  # Use the same interpreter to run the executor as we are using to run the framework
  file_path = os.path.dirname(os.path.abspath(sys.argv[0]))
  executor.command.value = "python %s/test_executor.py" % file_path
  # Pass the LD_LIBRARY_PATH through if we have it in the submission environment
  #if os.environ.has_key("LD_LIBRARY_PATH"):
  #  environment = executor.command.environment
  #  variable = environment.variables.add()
  #  variable.name = "LD_LIBRARY_PATH"
  #  variable.value = os.environ["LD_LIBRARY_PATH"]
  executor.name = "Test Executor (Python)"
  executor.source = "python_test"

  framework = mesos_pb2.FrameworkInfo()
  framework.user = "" # Have Mesos fill in the current user.
  framework.name = "Test Framework (Python)"

  # TODO(vinod): Make checkpointing the default when it is default
  # on the slave.
  if os.getenv("MESOS_CHECKPOINT"):
    logger.info("Enabling checkpoint for the framework")
    framework.checkpoint = True

  implicitAcknowledgements = 1
  if os.getenv("MESOS_EXPLICIT_ACKNOWLEDGEMENTS"):
    logger.info("Enabling explicit status update acknowledgements")
    implicitAcknowledgements = 0

  scheduler = TestScheduler(implicitAcknowledgements, executor)


  if os.getenv("MESOS_AUTHENTICATE"):
    logger.info("Enabling authentication for the framework")

    if not os.getenv("DEFAULT_PRINCIPAL"):
      logger.info("Expecting authentication principal in the environment")
      sys.exit(1);

    if not os.getenv("DEFAULT_SECRET"):
      logger.info("Expecting authentication secret in the environment")
      sys.exit(1);

    credential = mesos_pb2.Credential()
    credential.principal = os.getenv("DEFAULT_PRINCIPAL")
    credential.secret = os.getenv("DEFAULT_SECRET")

    framework.principal = os.getenv("DEFAULT_PRINCIPAL")

    driver = mesos.native.MesosSchedulerDriver(
      scheduler,
      framework,
      sys.argv[1],
      implicitAcknowledgements,
      credential)
  else:
    framework.principal = "test-framework-python"

    driver = mesos.native.MesosSchedulerDriver(
        scheduler,
        framework,
        sys.argv[1],
        implicitAcknowledgements)

  driver.start()
  should_exit = False
  def handler(signum, frame):
      logger.info("got signal %d, exit now" % signum)
      should_exit = True
  signal.signal(signal.SIGTERM, handler)
  signal.signal(signal.SIGHUP, handler)
  signal.signal(signal.SIGABRT, handler)
  signal.signal(signal.SIGQUIT, handler)

  status = 0
  while not should_exit and not scheduler.done:
      try:
          time.sleep(0.25)
      except KeyboardInterrupt,ex:
          break

  status = 0 if driver.stop() == mesos_pb2.DRIVER_STOPPED else 1
  if TOTAL_TASKS_2ND != 0:
      logger.info("finished first run with status %d" % status)
  else:
      logger.info("exiting with status %d" % status)
      sys.exit(status)

  # run again after driver stopped
  TOTAL_TASKS = TOTAL_TASKS_2ND
  scheduler.reset()
  driver.start()
  should_exit = False
  status = 0
  while not should_exit and not scheduler.done:
      try:
          time.sleep(0.25)
      except KeyboardInterrupt,ex:
          break

  status = 0 if driver.abort() == mesos_pb2.DRIVER_ABORTED else 1
  if TOTAL_TASKS_3RD != 0:
      logger.info("finished second run after stop with status %d" % status)
  else:
      driver.stop()
      logger.info("exiting with status %d" % status)
      sys.exit(status)

#  driver.stop()

  # run again after driver aborted
  TOTAL_TASKS = TOTAL_TASKS_3RD
  scheduler.reset()
  driver.start()
  should_exit = False
  status = 0
  while not should_exit and not scheduler.done:
      try:
          time.sleep(0.25)
      except KeyboardInterrupt,ex:
          break

  status = 0 if driver.abort() == mesos_pb2.DRIVER_ABORTED else 1
  driver.stop()
  logger.info("exiting after abort with status %d" % status)
  sys.exit(status)
