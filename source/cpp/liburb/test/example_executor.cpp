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

#include <thread>
#include <mesos/executor.hpp>

#include <stout/duration.hpp>
#include <stout/os.hpp>

using namespace mesos;

using std::cout;
using std::endl;
using std::string;

// VLOG allows to redirect the same output to the log file together with liburb output
// set GLOG_log_dir=/tmp in the framework environment to see this output in /tmp directroy

class TestExecutor : public Executor
{
public:
    TestExecutor():runningTasks(0), startedTasks(0), maxExecTasks(0)
    {
        cout << "TestExecutor: constructor" << endl;
        VLOG(1) << "TestExecutor: constructor";
    }

    virtual ~TestExecutor()
    {
        cout << "TestExecutor: destructor" << endl;
        VLOG(1) << "TestExecutor: destructor";
    }

    virtual void registered(ExecutorDriver* /*driver*/,
                          const ExecutorInfo& /*executorInfo*/,
                          const FrameworkInfo& /*frameworkInfo*/,
                          const SlaveInfo& slaveInfo)
    {
        cout << "TestExecutor: Registered executor on " << slaveInfo.hostname() << endl;
        VLOG(1) << "TestExecutor: Registered executor on " << slaveInfo.hostname();
    }

    virtual void reregistered(ExecutorDriver* driver,
                              const SlaveInfo& slaveInfo)
    {
        cout << "TestExecutor: Re-registered executor on " << slaveInfo.hostname() << ", joining worker" << endl;
        VLOG(1) << "TestExecutor: Re-registered executor on " << slaveInfo.hostname() << ", joining worker";
        worker.join();
        cout << "TestExecutor: Re-registered: aborting driver" << endl;
        VLOG(1) << "TestExecutor: Re-registered: aborting driver";
        driver->abort();
    }

    virtual void disconnected(ExecutorDriver* /*driver*/) {
        cout << "TestExecutor:disconnected" << endl;
        VLOG(1) << "TestExecutor:disconnected";
    }

    virtual void launchTask(ExecutorDriver* driver, const TaskInfo& task)
    {
        cout << "TestExecutor:launchTask: Starting task " << task.task_id().value() << endl;
        VLOG(1) << "TestExecutor:launchTask: Starting task " << task.task_id().value();

        TaskStatus status;
        status.mutable_task_id()->MergeFrom(task.task_id());
        status.set_state(TASK_RUNNING);

        std::string taskId = task.task_id().value();
        pDriver = driver;
        runningTasks++;
        startedTasks++;

        Option<int> sleepTime(1);
        if (task.has_executor()) {
            auto& executorInfo = task.executor();
            if (executorInfo.has_command()) {
                auto& commandInfo = executorInfo.command();
                if (commandInfo.has_environment()) {
                    auto& env = commandInfo.environment();
                    for (auto i = 0; i < env.variables_size(); i++) {
                        auto& variable = env.variables(i);
                        if (variable.name() == "TASK_SLEEP_TIME") {
                            sleepTime = std::stoi(variable.value());
                        } else if (variable.name() == "MAX_EXEC_TASKS") {
                            maxExecTasks = std::stoi(variable.value());
                        }
                    }
                }
            }
        }
        cout << "TestExecutor:launchTask: There are " << runningTasks << " running tasks" << endl;
        VLOG(1) << "TestExecutor:launchTask: There are " << runningTasks << " running tasks";
        worker = std::thread(&TestExecutor::doWork, this, taskId, sleepTime.get());

        driver->sendStatusUpdate(status);
        cout << "TestExecutor:launchTask: end" << endl;
        VLOG(1) << "TestExecutor:launchTask: end";
    }

    void doWork(std::string taskId, int sleepTime) {
        sleep(sleepTime);
        std::string message = "{ \"message\": \"Hello\", \"task\" : \"" + taskId +"\" }";
        pDriver->sendFrameworkMessage(message);
        cout << "TestExecutor:doWork done (slept for " << sleepTime << ") sec, sent message: " << message << endl;
        VLOG(1) << "TestExecutor:doWork done (slept for " << sleepTime << ") sec, sent message: " << message;
    }

    virtual void killTask(ExecutorDriver* /*driver*/, const TaskID& /*taskId*/) {
        cout << "TestExecutor:killTask" << endl;
        VLOG(1) << "TestExecutor:killTask";
    }

    virtual void frameworkMessage(ExecutorDriver* driver, const string& data) {
        // We are done when we get a response from the scheduler...
        cout << "TestExecutor:frameworkMessage: Received framework message [" << data << "]\n";
        VLOG(1) << "TestExecutor:frameworkMessage: Received framework message [" << data << "]";
        TaskInfo task;
        task.mutable_task_id()->set_value(data);
        TaskStatus status;
        status.mutable_task_id()->MergeFrom(task.task_id());
        status.set_state(TASK_FINISHED);
        cout << "TestExecutor:frameworkMessage: setting task state to FINISHED, join worker thread" << endl;
        VLOG(1) << "TestExecutor:frameworkMessage: setting task state to FINISHED, join worker thread";
        worker.join();
        cout << "TestExecutor:frameworkMessage: joined, sending status update" << endl;
        VLOG(1) << "TestExecutor:frameworkMessage: joined, sending status update";
        driver->sendStatusUpdate(status);
        runningTasks--;
        cout << "TestExecutor:frameworkMessage: There are " << runningTasks << " running tasks" << endl;
        VLOG(1) << "TestExecutor:frameworkMessage: There are " << runningTasks << " running tasks";
        if ((maxExecTasks != 0) && (startedTasks >= maxExecTasks)) {
            cout << "TestExecutor:frameworkMessage: aborting driver after " << startedTasks << " tasks ran" << endl;
            VLOG(1) << "TestExecutor:frameworkMessage: aborting driver after " << startedTasks << " tasks ran";
            driver->abort();
        }
    }

    virtual void shutdown(ExecutorDriver* /*driver*/) {
        cout << "TestExecutor:shutdown" << endl;
        VLOG(1) << "TestExecutor:shutdown";
    }

    virtual void error(ExecutorDriver* /*driver*/, const string& /*message*/) {
        cout << "TestExecutor:error" << endl;
        VLOG(1) << "TestExecutor:error";
    }

    std::thread worker;
    int runningTasks;
    int startedTasks;
    int maxExecTasks; // 0 means unlimited
    ExecutorDriver* pDriver;
};


int main(int /*argc*/, char** /*argv*/)
{
    TestExecutor executor;
    MesosExecutorDriver driver(&executor);
    FLAGS_v = 4;
    auto ret = driver.run();
    cout << "TestExecutor:main: driver ret = " << ret << ", all done" << endl;
    VLOG(1) << "TestExecutor:main: driver ret = " << ret << ", all done";
    return ret == DRIVER_STOPPED ? 0 : 1;
}
