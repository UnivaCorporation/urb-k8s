// Copyright 2017 Univa Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.


#include <iostream>
#include <string>
#include <sstream>
#include <exception>

#include <mesos/executor.hpp>
#include <mesos/mesos.hpp>
#include <mesos.pb.h>
#include <messages.pb.h>

#include <stout/os.hpp>
#include <stout/linkedhashmap.hpp>
#ifndef CV_0_24_1
#include "common/lock.hpp"
#endif

#include "timer.hpp"
#include <json_protobuf.h>
#include <message_broker.hpp>
#include <executor_process.hpp>

using namespace mesos;
using namespace mesos::internal;

using std::string;

std::once_flag exec_once;

// Implementation of C++ API.

MesosExecutorDriver::MesosExecutorDriver(Executor* _executor)
    : executor(_executor),
      process(NULL),
      status(DRIVER_NOT_STARTED)
{
    VLOG(1) << "MesosExecutorDriver::MesosExecutorDriver";
    GOOGLE_PROTOBUF_VERIFY_VERSION;

    // Create mutex and condition variable.
    pthread_mutexattr_t attr;
    pthread_mutexattr_init(&attr);
    pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_RECURSIVE);
    pthread_mutex_init(&mutex, &attr);
    pthread_mutexattr_destroy(&attr);
    pthread_cond_init(&cond, 0);

    // Log to warnings stderr by default
    Option<std::string> loglevel = os::getenv("URB_LOGLEVEL");
    if (loglevel.isNone() || loglevel.get().empty()) {
        FLAGS_minloglevel = 1;
    } else {
        try {
            FLAGS_minloglevel = std::stoi(loglevel.get());
        } catch (std::exception& e) {
            std::cerr << "Exception for URB_LOGLEVEL=" << loglevel.get() << ": " << e.what();
        }
    }
    if (FLAGS_log_dir.empty()) {
        FLAGS_logtostderr = 1;
    }

    std::call_once(exec_once, google::InitGoogleLogging, "urb");
}


MesosExecutorDriver::~MesosExecutorDriver()
{
    VLOG(1) << "MesosExecutorDriver::~MesosExecutorDriver";
    if(process != NULL) {
        delete process;
    }
}


Status MesosExecutorDriver::start()
{
    VLOG(1) << "MesosExecutorDriver::start";
#ifdef CV_0_24_1
    std::lock_guard<std::recursive_mutex> lock(mutex);
#else
    Lock lock(&mutex);
#endif

    Option<std::string> value;

    SlaveID slaveId;
    FrameworkID frameworkId;
    ExecutorID executorId;

    // Get slave ID from environment.
    value = os::getenv("URB_SLAVE_ID");
    if (value.isSome()) {
        slaveId.set_value(value.get());
    } else {
        LOG(ERROR) << "MesosExecutorDriver::start: URB_SLAVE_ID not defined";
    }

    // Get framework ID from environment.
    value = os::getenv("URB_FRAMEWORK_ID");
    if (value.isSome()) {
        frameworkId.set_value(value.get());
    } else {
        LOG(ERROR) << "MesosExecutorDriver::start: URB_FRAMEWORK_ID not defined";
    }

    // Get executor ID from environment.
    value = os::getenv("URB_EXECUTOR_ID");
    if (value.isSome()) {
        executorId.set_value(value.get());
    } else {
        LOG(ERROR) << "MesosExecutorDriver::start: URB_EXECUTOR_ID not defined";
    }

    CHECK(process == NULL);
    process = new UrbExecutorProcess(this,
        executor,
        frameworkId,
        executorId,
        slaveId);

    process->startRegistration();

    LOG(INFO) << "Executor start";
    if (status != DRIVER_NOT_STARTED) {
        VLOG(1) << "MesosExecutorDriver::start: not started";
        return status;
    }

    VLOG(1) << "MesosExecutorDriver::start: end";
    return status = DRIVER_RUNNING;
}


Status MesosExecutorDriver::stop()
{
    VLOG(1) << "MesosExecutorDriver::stop";
#ifdef CV_0_24_1
    std::lock_guard<std::recursive_mutex> lock(mutex);
#else
    Lock lock(&mutex);
#endif

    if (status != DRIVER_RUNNING && status != DRIVER_ABORTED) {
        VLOG(1) << "MesosExecutorDriver::stop: driver is not running and not aborted, return";
        return status;
    }

    CHECK(process != NULL);

    bool aborted = (status == DRIVER_ABORTED);

    status = DRIVER_STOPPED;

    // Signal the shutdown
#ifdef CV_0_24_1
    cond.notify_one();
#else
    pthread_cond_signal(&cond);
    lock.unlock();
#endif

    VLOG(1) << "MesosExecutorDriver::stop: end";

    return aborted ? DRIVER_ABORTED : status;
}


Status MesosExecutorDriver::abort()
{
    VLOG(1) << "MesosExecutorDriver::abort";
#ifdef CV_0_24_1
    std::lock_guard<std::recursive_mutex> lock(mutex);
#else
    Lock lock(&mutex);
#endif

    if (status != DRIVER_RUNNING) {
        VLOG(1) << "MesosExecutorDriver::abort: driver is not running, return";
        return status;
    }

    CHECK(process != NULL);

    process->abort();
#ifdef CV_0_24_1
    cond.notify_one();
#else
    pthread_cond_signal(&cond);
#endif
    VLOG(1) << "MesosExecutorDriver::abort: end";
    return status = DRIVER_ABORTED;
}


Status MesosExecutorDriver::join()
{
    VLOG(1) << "MesosExecutorDriver::join";
#ifdef CV_0_24_1
    std::unique_lock<std::recursive_mutex> lock(mutex);
#else
    Lock lock(&mutex);
#endif

    if (status != DRIVER_RUNNING) {
        VLOG(1) << "MesosExecutorDriver::join: driver is not running, return";
        return status;
    }

    while (status == DRIVER_RUNNING) {
        VLOG(1) << "MesosExecutorDriver::join: waiting on condition variable";
#ifdef CV_0_24_1
        cond.wait(lock);
#else
        pthread_cond_wait(&cond, &mutex);
#endif
    }

    CHECK(status == DRIVER_ABORTED || status == DRIVER_STOPPED);

    VLOG(1) << "MesosExecutorDriver::join: end";

    return status;
}


Status MesosExecutorDriver::run()
{
    VLOG(1) << "MesosExecutorDriver::run";
    Status status = start();
    VLOG(1) << "MesosExecutorDriver::run: end";
    return status != DRIVER_RUNNING ? status : join();
}


Status MesosExecutorDriver::sendStatusUpdate(const TaskStatus& taskStatus)
{
    VLOG(1) << "MesosExecutorDriver::sendStatusUpdate: task state=" << TaskState_Name(taskStatus.state());
#ifdef CV_0_24_1
    std::lock_guard<std::recursive_mutex> lock(mutex);
#else
    Lock lock(&mutex);
#endif

    if (status != DRIVER_RUNNING) {
        VLOG(1) << "MesosExecutorDriver::sendStatusUpdate: driver is not running, return";
        return status;
    }

    CHECK(process != NULL);

    process->sendStatusUpdate(taskStatus);

    VLOG(1) << "MesosExecutorDriver::sendStatusUpdate: end";

    return status;
}


Status MesosExecutorDriver::sendFrameworkMessage(const string& data)
{
    VLOG(1) << "MesosExecutorDriver::sendFrameworkMessage";
#ifdef CV_0_24_1
    std::lock_guard<std::recursive_mutex> lock(mutex);
#else
    Lock lock(&mutex);
#endif

    if (status != DRIVER_RUNNING) {
        VLOG(1) << "MesosExecutorDriver::sendFrameworkMessage: driver is not running, return";
        return status;
    }

    CHECK(process != NULL);

    process->sendFrameworkMessage(data);

    VLOG(1) << "MesosExecutorDriver::sendFrameworkMessage: end";

    return status;
}
