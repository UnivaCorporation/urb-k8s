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
const int32_t TOTAL_TASKS = 23;

class TestScheduler : public Scheduler
{
public:
  TestScheduler(const ExecutorInfo& _executor, const string& _role)
    : executor(_executor),
      role(_role),
      tasksLaunched(0),
      tasksFinished(0),
      totalTasks(TOTAL_TASKS),
      offersReceived(0) {
    for(int i=0; i < TOTAL_TASKS; i++) {
        results.push_back(false);
    }
  }

  virtual ~TestScheduler() {}

  virtual void registered(SchedulerDriver*,
                          const FrameworkID&,
                          const MasterInfo&)
  {
    cout << "Registered!" << endl;
  }

  virtual void reregistered(SchedulerDriver*, const MasterInfo&) {}

  virtual void disconnected(SchedulerDriver*) {}

  TaskInfo launchTask(const Offer &offer, Resources &remaining, const Resources &TASK_RESOURCES, int &taskId) {
        cout << "\t\tStarting task " << taskId << " on "
             << offer.hostname() << " under offer " << offer.id().value() << endl;

        TaskInfo task;
        task.set_name("Task " + std::to_string(taskId));
        task.mutable_task_id()->set_value(std::to_string(taskId));
        task.mutable_slave_id()->MergeFrom(offer.slave_id());
        task.mutable_executor()->MergeFrom(executor);

        Option<Resources> resources = remaining.find(TASK_RESOURCES);
        CHECK_SOME(resources);
        task.mutable_resources()->MergeFrom(resources.get());
        remaining -= resources.get();
        return task;
  }

  virtual void resourceOffers(SchedulerDriver* driver,
                              const vector<Offer>& offers)
  {
    time_t now = time(0);
    offersReceived+=offers.size();
    cout << asctime(localtime(&now)) << ": Offer contains: " << offers.size() << " offers. (total received: " <<  offersReceived << ")" << endl;
    // Launch tasks.
    vector<TaskInfo> tasks;
    vector<OfferID> offerIds;
    if(offersReceived < 10 || offersReceived > 40) {
    for (size_t i = 0; i < offers.size(); i++) {
      const Offer& offer = offers[i];
      bool tasksInOffer = false;

      static const Resources TASK_RESOURCES = Resources::parse(
          "cpus:" + stringify(CPUS_PER_TASK) +
          ";mem:" + stringify(MEM_PER_TASK)).get();

      Resources remaining = offer.resources();
      cout << "\tOffer Resources for slave: [" << offer.slave_id().value() << "]: " << remaining << endl;

      while (tasksLaunched < totalTasks &&
              remaining.toUnreserved().contains(TASK_RESOURCES)) {
        int taskId = tasksLaunched++;

        TaskInfo task = launchTask(offer, remaining, TASK_RESOURCES, taskId);
        tasksInOffer = true;
        cout << "\t\tRemaining Resources: " << remaining << endl;

        tasks.push_back(task);
      }
      if(tasks.size() == 0) {
          cout << "\tNo tasks launched. " <<endl;
          cout << "\t\t" << (totalTasks - tasksLaunched) << " tasks left to launch." << endl;
          cout << "\t\t" << (totalTasks - tasksFinished) << " tasks left to complete." << endl;
          if ( (totalTasks - tasksLaunched) == 0) {
              for(int i =0; i < totalTasks; i++) {
                  if(! results[i]) {
                      cout << "\t\t\tTASK: " << i << " still pending/running/lost." << endl;
                  }
              }
          }
          cout << "\t\t" << lostTasks.size() << " tasks were definitely lost." << endl;
          for(std::vector<int>::iterator it = lostTasks.begin(); it != lostTasks.end();) {
              cout << "\t\t\tTASK: " << *it << " lost....";
              if (remaining.toUnreserved().contains(TASK_RESOURCES)) {
                  cout << " relaunching." << endl;
                  tasks.push_back(launchTask(offer, remaining, TASK_RESOURCES, *it));
                  tasksInOffer = true;
                  lostTasks.erase(it);
              } else {
                  cout << " not enough resources to relaunch." << endl;
                  ++it;
              }
          }
      }
      // If we have a task we are using this offer
      if(tasksInOffer) {
          offerIds.push_back(offer.id());
      }
    }
    cout << "Sending launch tasks message to master with: " << tasks.size() << " task(s)" << endl;
    driver->launchTasks(offerIds, tasks);
    } else {
        for (size_t i = 0; i < offers.size(); i++) {
          cout << "\tOffer contains slave slave: [" << offers[i].slave_id().value() << "]" << endl;
          offerIds.push_back(offers[i].id());
        }
        if (offersReceived > 20) {
            Filters f;
            f.set_refuse_seconds(15);
            cout << "Sending launch tasks message to master rejecting: " <<  offerIds.size() << " offers(s) with refuse_seconds: 15" << endl;
            driver->launchTasks(offerIds,vector<TaskInfo>(), f);
            if(offersReceived > 30) {
                cout << "Reviving offers... should get an offer almost immediately" << endl;
                driver->reviveOffers();
            }
        } else {
            cout << "Sending launch tasks message to master rejecting: " <<  offerIds.size() << " offers(s)" << endl;
            driver->launchTasks(offerIds,vector<TaskInfo>());
        }
    }
  }

  virtual void offerRescinded(SchedulerDriver*,
                              const OfferID&) {}

  virtual void statusUpdate(SchedulerDriver* driver, const TaskStatus& status)
  {
    int taskId = std::stoi(status.task_id().value());

    cout << "Task " << taskId << " is in state " << status.state() << endl;

    if(results[taskId]) {
        cout << "DUPLICATE MESSAGE FOR TASK ID (this is OK but should be rare): " << taskId << endl;
        return;
    }

    if (status.state() == TASK_FINISHED) {
      tasksFinished++;
      results[taskId] = true;
    }

    if (status.state() == TASK_LOST) {
        lostTasks.push_back(taskId);
    }

    if (tasksFinished == totalTasks) {
      driver->stop();
      for(int i =0; i < TOTAL_TASKS; i++) {
          if(! results[i]) {
              cout << "TASK: " << i << " never completed!!!!!" << endl;
          }
      }
    }
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

  virtual void slaveLost(SchedulerDriver*, const SlaveID&) {}

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
  int offersReceived;
  std::vector<bool> results;
  std::vector<int> lostTasks;
};
int main(int, char** argv)
{
    // Find this executable's directory to locate executor.
    string path = os::realpath(Path(argv[0]).dirname()).get();
    string uri = path + "/example_executor.test";

    // Build up executor object
    ExecutorInfo executor;
    executor.mutable_executor_id()->set_value("default");
    executor.mutable_command()->set_value(uri);
    executor.set_name("Test Executor (C++)");
    executor.set_source("cpp_test");

    //Create out scheduler instance to pass to the framework
    TestScheduler scheduler(executor, "*");

    FrameworkInfo framework;
    framework.set_user("");
    framework.set_name("Test Framework (C++)");
    framework.set_role("*");

    // Create the scheduler driver from the liburb library
    MesosSchedulerDriver* driver;
    driver = new MesosSchedulerDriver(
        &scheduler, framework, "urb://localhost");
       // &scheduler, framework, "urb://ha://localhost/mymaster");

    //system("python test/simple_master.py one_shot &");

    int status = driver->run() == DRIVER_STOPPED ? 0 : 1;

    driver->stop();

    delete driver;
    return status;
}
