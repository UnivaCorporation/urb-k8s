/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
#include <iostream>
#include <string>

#include <mesos/resources.hpp>
#include <mesos/scheduler.hpp>

#include <stout/check.hpp>
#include <stout/exit.hpp>
#include <stout/flags.hpp>
#include <stout/os.hpp>
#include <stout/stringify.hpp>

#include <json/json.h>

#include <glog/logging.h>

using namespace mesos;

using std::cerr;
using std::cout;
using std::endl;
using std::flush;
using std::string;
using std::vector;

const int32_t CPUS_PER_TASK = 1;
const int32_t MEM_PER_TASK = 32;
const int32_t TOTAL_TASKS = 10;

class TestScheduler : public Scheduler
{
public:
  TestScheduler(const string& _role)
    :
      role(_role),
      tasksLaunched(0),
      tasksFinished(0),
      totalTasks(TOTAL_TASKS) {}

  virtual ~TestScheduler() {}

  virtual void registered(SchedulerDriver*,
                          const FrameworkID&,
                          const MasterInfo&)
  {
    cout << "Registered!" << endl;
  }

  virtual void reregistered(SchedulerDriver*, const MasterInfo& /*masterInfo*/) {}

  virtual void disconnected(SchedulerDriver* /*driver*/) {}

  virtual void resourceOffers(SchedulerDriver* driver,
                              const vector<Offer>& offers)
  {
    cout << "." << flush;
    for (size_t i = 0; i < offers.size(); i++) {
      const Offer& offer = offers[i];

      static const Resources TASK_RESOURCES = Resources::parse(
          "cpus:" + stringify(CPUS_PER_TASK) +
          ";mem:" + stringify(MEM_PER_TASK)).get();

      Resources remaining = offer.resources();

      // Launch tasks.
      vector<TaskInfo> tasks;
      while (tasksLaunched < totalTasks &&
              remaining.toUnreserved().contains(TASK_RESOURCES)) {
        int taskId = tasksLaunched++;

        cout << "Starting task " << taskId << " on "
             << offer.hostname() << endl;

        TaskInfo task;
        task.set_name("Task " + std::to_string(taskId));
        task.mutable_task_id()->set_value(std::to_string(taskId));
        task.mutable_slave_id()->MergeFrom(offer.slave_id());
        task.mutable_command()->set_value("/bin/bash -c 'echo hello world'");

        Option<Resources> resources = remaining.find(TASK_RESOURCES);
        CHECK_SOME(resources);
        task.mutable_resources()->MergeFrom(resources.get());
        remaining -= resources.get();

        tasks.push_back(task);
      }

      driver->launchTasks(offer.id(), tasks);
    }
  }

  virtual void offerRescinded(SchedulerDriver* /*driver*/,
                              const OfferID& /*offerId*/) {}

  virtual void statusUpdate(SchedulerDriver* driver, const TaskStatus& status)
  {
    int taskId = std::stoi(status.task_id().value());

    cout << "Task " << taskId << " is in state " << status.state() << endl;

    if (status.state() == TASK_FINISHED)
      tasksFinished++;

    if (tasksFinished == totalTasks)
      driver->stop();
  }

  virtual void frameworkMessage(SchedulerDriver* driver,
                                const ExecutorID& executorId,
                                const SlaveID& slaveId,
                                const string& data) {

      cout << "Received framework message: [" << data << "]\n";
      Json::Value val;
      Json::Reader reader;
      bool ret = reader.parse(data,val);
      if(!ret) {
          cout << reader.getFormattedErrorMessages();
          return;
      }
      std::string value = val.get("task","").asString();
      driver->sendFrameworkMessage(executorId,slaveId,value);
  }

  virtual void slaveLost(SchedulerDriver* /*driver*/, const SlaveID& /*sid*/) {}

  virtual void executorLost(SchedulerDriver* /*driver*/,
                            const ExecutorID& /*executorID*/,
                            const SlaveID& /*slaveID*/,
                            int /*status*/) {}

  virtual void error(SchedulerDriver* /*driver*/, const string& message)
  {
    cout << message << endl;
  }

private:
  const ExecutorInfo executor;
  string role;
  int tasksLaunched;
  int tasksFinished;
  int totalTasks;
};
int main(int /*argc*/, char** argv)
{
    // Find this executable's directory to locate executor.
    string path = os::realpath(Path(argv[0]).dirname()).get();
    string uri = path + "/example_executor.test";

    //Create out scheduler instance to pass to the framework
    TestScheduler scheduler("*");

    FrameworkInfo framework;
    framework.set_user("");
    framework.set_name("Test Framework (C++)");
    framework.set_role("*");

    // Create the scheduler driver from the liburb library
    std::string url = "urb://localhost";
    MesosSchedulerDriver* driver;
    driver = new MesosSchedulerDriver(
        &scheduler, framework, url);

    //system("python test/simple_master.py one_shot &");

    int status = driver->run() == DRIVER_STOPPED ? 0 : 1;

    driver->stop();

    delete driver;
    return status;
}
