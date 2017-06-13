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
#include <map>
#include <set>

#include <mesos/resources.hpp>
#include <mesos/scheduler.hpp>

#include <stout/check.hpp>
#include <stout/exit.hpp>
#include <stout/flags.hpp>
#include <stout/os.hpp>
#include <stout/stringify.hpp>

#include <json/json.h>

//#include <glog/logging.h>

#include <ctime>   // localtime
#include <sstream> // stringstream


using namespace mesos;

using std::cerr;
using std::cout;
using std::endl;
using std::flush;
using std::string;
using std::vector;

const float CPUS_PER_TASK = 1;
const int MEM_PER_TASK = 32;
const int PORTS_BASE = 31000;
const int TOTAL_TASKS = 50; // default number of tasks
const int TASK_SLEEP_TIME = 1; // sleep time for task

std::string curr_td() {
  char buffer[26];
  int millisec;
  struct tm* tm_info;
  struct timeval tv;

  gettimeofday(&tv, NULL);

  millisec = lrint(tv.tv_usec/1000.0); // Round to nearest millisec
  if (millisec>=1000) { // Allow for rounding up to nearest second
    millisec -=1000;
    tv.tv_sec++;
  }

  tm_info = localtime(&tv.tv_sec);
  strftime(buffer, 26, "%Y:%m:%d %H:%M:%S", tm_info);
  std::stringstream ss;
  ss << buffer << "." << millisec << ": ";
  return ss.str();
}


class TestScheduler : public Scheduler
{
public:
  TestScheduler(const ExecutorInfo& executor, const string& role, int tasks, Option<std::string>& customResource)
    : executor_(executor),
      role_(role),
      totalTasks_(tasks),
      results_(tasks, false),
      customResource_(customResource)
  {
      cout << curr_td() << "example_framework: TestScheduler()" << endl;
      if (!customResource_.isNone()) {
          cout << curr_td() << "custom resource: " << customResource_.get() << endl;
      }
  }

  virtual ~TestScheduler() {
      cout << curr_td() << "example_framework: ~TestScheduler()" << endl;
  }

  virtual void registered(SchedulerDriver*,
                          const FrameworkID& fid,
                          const MasterInfo&)
  {
    cout << curr_td() << "example_framework: Registered: " << fid.value() << endl;
  }

  virtual void reregistered(SchedulerDriver*, const MasterInfo&)
  {
      cout << curr_td() << "example_framework: Reregistered" << endl;
  }

  virtual void disconnected(SchedulerDriver*)
  {
      cout << curr_td() << "example_framework: Disconnected" << endl;
  }

  TaskInfo launchTask(const Offer &offer, Resources &remaining, const Resources &TASK_RESOURCES, const int &taskId) {
        cout << curr_td() << "\t\tStarting Task " << taskId << " on "
             << offer.hostname() << " under offer " << offer.id().value() << endl;

        TaskInfo task;
        task.set_name("C++ Task " + std::to_string(taskId));
        task.mutable_task_id()->set_value(std::to_string(taskId));
        task.mutable_slave_id()->MergeFrom(offer.slave_id());
        task.mutable_executor()->MergeFrom(executor_);

        Option<Resources> resources = remaining.find(TASK_RESOURCES);
        CHECK_SOME(resources);
        task.mutable_resources()->MergeFrom(resources.get());
        remaining -= resources.get();
        return task;
  }

  virtual void resourceOffers(SchedulerDriver* driver,
                              const vector<Offer>& offers)
  {
    cout << curr_td() << "example_framework: Offer contains: " << offers.size() << " offers" << endl;
    cout << curr_td() << "example_framework: Tasks launched=" << tasksLaunched_ << endl;
    static const auto cust = (customResource_.isNone()) ? "" : ";" + customResource_.get();
    static const Resources TASK_RESOURCES = Resources::parse(
        "cpus:" + stringify(CPUS_PER_TASK) +
        ";mem:" + stringify(MEM_PER_TASK) +
        cust).get();
    bool reconcile = true;

    for (size_t offer_cnt = 0; offer_cnt < offers.size(); offer_cnt++) {
      const Offer& offer = offers[offer_cnt];

      Resources remaining = offer.resources();
      cout << curr_td() << "\tOffer [" << offer.id().value() << "] resources for slave: [" << offer.slave_id().value() << "]: " << remaining << endl;

      // Launch tasks.
      vector<TaskInfo> tasks;
      while (tasksLaunched_ < totalTasks_ &&
             remaining.flatten().contains(TASK_RESOURCES)) {
        int taskId = tasksLaunched_++;

        TaskInfo task = launchTask(offer, remaining, TASK_RESOURCES, taskId);
        cout << curr_td() << "\t\tRemaining Resources: " << remaining << endl;

        tasks.push_back(task);
      }
      if (tasks.size() == 0) {
          cout << curr_td() << "\tNo tasks launched. " <<endl;
          cout << curr_td() << "\t\t" << (totalTasks_ - tasksLaunched_) << " tasks left to launch." << endl;
          cout << curr_td() << "\t\t" << (totalTasks_ - tasksFinished_) << " tasks left to complete." << endl;
          if ((totalTasks_ - tasksLaunched_) == 0) {
              std::vector<TaskStatus> statuses;
              for (int i = 0; i < totalTasks_; i++) {
                  if (!results_[i]) {
                      cout << curr_td() << "\t\t\tTask " << i << " still pending/running/lost." << endl;
                      TaskStatus status;
                      std::string tid = std::to_string(i);
                      status.mutable_task_id()->set_value(tid);
                      status.set_state(TASK_RUNNING);
                      statuses.push_back(status);
                  }
              }
              // Issue a reconcile once
              if (reconcile) {
                  reconcile = false;
                  cout << curr_td() << "\t\tSending reconcile tasks request to master" << endl;
                  driver->reconcileTasks(statuses);
              }
          }
          cout << curr_td() << "\t\t" << lostTasks_.size() << " tasks were definitely lost." << endl;
          for (auto it = lostTasks_.begin(); it != lostTasks_.end();) {
              cout << curr_td() << "\t\t\tTask " << *it << " lost...";
              if (remaining.flatten().contains(TASK_RESOURCES)) {
                  cout << " relaunching." << endl;
                  tasks.push_back(launchTask(offer, remaining, TASK_RESOURCES, *it));
                  it = lostTasks_.erase(it);
              } else {
                  cout << " not enough resources to relaunch." << endl;
                  cout << curr_td() << "\t\t\tremaining: [" << offer.id().value() << "], ["
                       << offer.slave_id().value() << "]: " << remaining << endl;
                  cout << curr_td() << "\t\t\trequired: " << TASK_RESOURCES << endl;
                  ++it;
              }
          }
      } else {
          cout << curr_td() << "example_framework: Sending launch tasks message to master with: " << tasks.size() << " task(s)" << endl;
      }
      driver->launchTasks(offer.id(), tasks);
    }
  }

  virtual void offerRescinded(SchedulerDriver* /*driver*/,
                              const OfferID& /*offerId*/)
  {
      cout << curr_td() << "example_framework: offerRescinded" << endl;
  }

  virtual void statusUpdate(SchedulerDriver* driver, const TaskStatus& status)
  {
    int taskId = std::stoi(status.task_id().value());

    auto state = status.state();
    cout << curr_td() << "example_framework: statusUpdate: Task " << taskId << " is in state " << stateStr(state) << endl;

    if (results_[taskId]) {
        cout << curr_td() << "example_framework: statusUpdate: DUPLICATE MESSAGE FOR TASK ID (this is OK but should be rare): " << taskId << endl;
        return;
    }

    switch (state) {
    case TASK_FINISHED:
        tasksFinished_++;
        results_[taskId] = true;
        cout << curr_td() << "example_framework: statusUpdate: Task " << taskId << " finished" << endl;
        if (lostTasks_.erase(taskId)) {
            cout << curr_td() << "example_framework: statusUpdate: Task " << taskId << " removed from lost list" << endl;
        }
        break;
    case TASK_LOST:
        lostTasks_.insert(taskId);
        cout << curr_td() << "example_framework: statusUpdate: Task " << taskId << " lost" << endl;
        break;
    default:
        if (lostTasks_.erase(taskId)) {
            cout << curr_td() << "example_framework: statusUpdate: Task " << taskId << " removed from lost list" << endl;
        }
        break;
    }

    cout << curr_td() << "example_framework: statusUpdate: tasks: total=" << totalTasks_ << ", finished=" << tasksFinished_
         << ", lost=" << lostTasks_.size() << endl;

    if (tasksFinished_ == totalTasks_) {
        cout << curr_td() << "example_framework: statusUpdate: total tasks " << totalTasks_ << " finished\nstopping driver" << endl;
        driver->stop();
        cout << curr_td() << "example_framework: statusUpdate: driver stopped" << endl;
        for (int i =0; i < totalTasks_; i++) {
            if (!results_[i]) {
                cout << curr_td() << "example_framework: Task " << i << " never completed!!!!!" << endl;
            }
        }
    }
  }

  virtual void frameworkMessage(SchedulerDriver* driver,
                                const ExecutorID& executorId,
                                const SlaveID& slaveId,
                                const string& data) {

      cout << curr_td() << "example_framework: Received framework message: [" << data << "]" << endl;
      Json::Value val;
      Json::Reader reader;
      bool ret = reader.parse(data,val);
      if (!ret) {
          cout << curr_td() << "parse error: " << reader.getFormattedErrorMessages();
          return;
      }
      std::string value = val.get("task", "").asString();
      cout << curr_td() << "example_framework: Sending back framework message: [" << value << "] to execitor '"
           << executorId.value() << "' on slave '" << slaveId.value() << "'" << endl;
      driver->sendFrameworkMessage(executorId, slaveId, value);
      cout << curr_td() << "example_framework: Sent back framework message: [" << value << "]" << endl;
  }

  virtual void slaveLost(SchedulerDriver* /*driver*/, const SlaveID& /*sid*/)
  {
      cout << curr_td() << "example_framework: slaveLost" << endl;
  }

  virtual void executorLost(SchedulerDriver* /*driver*/,
                            const ExecutorID& /*executorID*/,
                            const SlaveID& /*slaveID*/,
                            int /*status*/)
  {
      cout << curr_td() << "example_framework: executorLost" << endl;
  }

  virtual void error(SchedulerDriver* /*driver*/, const string& message)
  {
      cout << curr_td() << "example_framework: error: " << message << endl;
  }

private:
  const std::string& stateStr(TaskState& state) {
      static const std::string undefined("undefined");
      static const std::map<TaskState, std::string> m {
          {TASK_FINISHED, "TASK_FINISHED"},
          {TASK_FAILED, "TASK_FAILED"},
          {TASK_KILLED, "TASK_KILLED"},
          {TASK_LOST, "TASK_LOST"},
          {TASK_STAGING, "TASK_STAGING"},
          {TASK_STARTING, "TASK_STARTING"},
          {TASK_RUNNING, "TASK_RUNNING"}
      };
      auto it = m.find(state);
      if (it != m.end())
          return it->second;
      else
          return undefined;
  }

  const ExecutorInfo executor_;
  string role_;
  int totalTasks_;
  int tasksLaunched_ = 0;
  int tasksFinished_ = 0;
  std::vector<bool> results_;
  std::set<int> lostTasks_;
  Option<std::string> customResource_;
};


int main(int argc, char** argv)
{
    int tasks = TOTAL_TASKS;
    Option<std::string> sleepTime;
    Option<std::string> maxExecutorTasks;
    Option<std::string> customResource;
    if (argc == 2) {
        tasks = std::stoi(argv[1]);
        cout << curr_td() << "total tasks: " << tasks << endl;
    } else if (argc == 3) {
        tasks = std::stoi(argv[1]);
        sleepTime = argv[2];
        cout << curr_td() << "total tasks: " << tasks << ", task sleep time: " << sleepTime.get() << endl;
    } else if (argc == 4) {
        tasks = std::stoi(argv[1]);
        sleepTime = argv[2];
        maxExecutorTasks = argv[3]; // maximum numer of tasks to run in executor
        cout << curr_td() << "total tasks: " << tasks << ", task sleep time: " << sleepTime.get()
             << ", max executor tasks: " << maxExecutorTasks.get() << endl;
    } else if (argc == 5) {
        tasks = std::stoi(argv[1]);
        sleepTime = argv[2];
        maxExecutorTasks = argv[3]; // maximum numer of tasks to run in executor
        customResource = argv[4]; // should be provided in form name:value (dfsio_spindles:1)
        cout << curr_td() << "total tasks: " << tasks << ", task sleep time: " << sleepTime.get()
             << ", max executor tasks: " << maxExecutorTasks.get()
             << ", custom resource: " << customResource.get() << endl;
    }

    // Find this executable's directory to locate executor.
    string path = os::realpath(Path(argv[0]).dirname()).get();
    string uri = path + "/example_executor.test";
    Option<string> master = os::getenv("URB_MASTER");
    if (master.isNone()) {
        master = "urb://localhost";
    }

    // Build up executor object
    ExecutorInfo executor;
    executor.mutable_executor_id()->set_value("default");
    executor.mutable_command()->set_value(uri);
    executor.set_name("Test Executor (C++)");
    executor.set_source("cpp_test");
    Environment* environment = executor.mutable_command()->mutable_environment();
    Environment_Variable* variableUrblog = environment->add_variables();
    variableUrblog->set_name("URB_LOGLEVEL");
    variableUrblog->set_value("0");
    Option<string> glog_val = os::getenv("GLOG_v");
    if (!glog_val.isNone()) {
        Environment_Variable* variableGlog = environment->add_variables();
        variableGlog->set_name("GLOG_v");
        variableGlog->set_value(glog_val.get());
    }
    if (!sleepTime.isNone()) {
        Environment_Variable* variableSleep = environment->add_variables();
        variableSleep->set_name("TASK_SLEEP_TIME");
        variableSleep->set_value(sleepTime.get());
    }
    if (!maxExecutorTasks.isNone()) {
        Environment_Variable* variableMaxExecTasks = environment->add_variables();
        variableMaxExecTasks->set_name("MAX_EXEC_TASKS");
        variableMaxExecTasks->set_value(maxExecutorTasks.get());
    }

    //Create out scheduler instance to pass to the framework
    TestScheduler scheduler(executor, "*", tasks, customResource);

    FrameworkInfo framework;
    framework.set_user("");
    framework.set_name("Test Framework (C++)");
    framework.set_role("*");

    // Create the scheduler driver from the liburb library
    MesosSchedulerDriver* driver;
    driver = new MesosSchedulerDriver(
        &scheduler, framework, master.get());
       // &scheduler, framework, "urb://ha://localhost/mymaster");

    //system("python test/simple_master.py one_shot &");

    int status = driver->run() == DRIVER_STOPPED ? 0 : 1;
    cout << curr_td() << "example_framework: driver->run() exited with status: " << status << endl;
    driver->stop();
    cout << curr_td() << "example_framework: after driver->stop()" << endl;
    delete driver;
    cout << curr_td() << "example_framework: all done" << endl;
    return status;
}
