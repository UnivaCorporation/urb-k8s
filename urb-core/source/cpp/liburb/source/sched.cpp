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
#include <map>
#include <string>
#include <sstream>
#include <vector>
#include <mutex>
#include <memory>
#include <exception>

#include <glog/logging.h>

#include <mesos/scheduler.hpp>
#include <mesos.pb.h>
#include <messages.pb.h>
#ifndef CV_0_24_1
#include <common/lock.hpp>
#endif

#include <stout/os.hpp>

#include "timer.hpp"
#include <json_protobuf.h>
#include <message_broker.hpp>
#include <scheduler_process.hpp>


using namespace mesos;

using std::map;
using std::string;
using std::vector;


// Implementation of C++ API.
//

std::once_flag once;
 
MesosSchedulerDriver::MesosSchedulerDriver(
    Scheduler* _scheduler,
    const FrameworkInfo& _framework,
    const string& _master,
    bool _implicitAcknowledgements):
      detector(NULL),
      scheduler(_scheduler),
      framework(_framework),
      master(_master),
      process(NULL),
      status(DRIVER_NOT_STARTED),
      implicitAcknowlegements(_implicitAcknowledgements),
      credential(NULL)
{
    GOOGLE_PROTOBUF_VERIFY_VERSION;

    //Log to warnings stderr by default
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
    std::call_once(once, google::InitGoogleLogging, framework.name().c_str());

    VLOG(1) << "\tMaster: " << master;
    VLOG(1) << "\tFramework Name: " << *framework.mutable_name();
    VLOG(1) << "\tFramework User: " << *framework.mutable_user();
    VLOG(1) << "\tFramework Role: " << *framework.mutable_role();

#ifndef CV_0_24_1
    pthread_mutexattr_t attr;
    pthread_mutexattr_init(&attr);
    pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_RECURSIVE);
    pthread_mutex_init(&mutex, &attr);
    pthread_mutexattr_destroy(&attr);
    pthread_cond_init(&cond, 0);
#endif
    // See FrameWorkInfo in include/mesos/mesos.proto:
    if (framework.user().empty()) {
        Result<string> user = os::user();
        CHECK_SOME(user);

        framework.set_user(user.get());
    }

    CHECK(process == NULL);

    url = master;
    VLOG(1) << "MesosSchedulerDriver::MesosSchedulerDriver(): 1 end: status=" << status;
}


// duplicated from above but without implicitAcknowlegements in order
// to be easily removable as deprecated in the future
MesosSchedulerDriver::MesosSchedulerDriver(
    Scheduler* _scheduler,
    const FrameworkInfo& _framework,
    const string& _master):
      detector(NULL),
      scheduler(_scheduler),
      framework(_framework),
      master(_master),
      process(NULL),
      status(DRIVER_NOT_STARTED),
      implicitAcknowlegements(true),
      credential(NULL)
{
    GOOGLE_PROTOBUF_VERIFY_VERSION;

    //Log to warnings stderr by default
    Option<std::string> loglevel = os::getenv("URB_LOGLEVEL");
    if (loglevel.isNone() || loglevel.get().empty()) {
        FLAGS_minloglevel = 1;
    } else {
        FLAGS_minloglevel = std::stoi(loglevel.get());
    }
    if (FLAGS_log_dir.empty()) {
        FLAGS_logtostderr = 1;
    }
    std::call_once(once, google::InitGoogleLogging, framework.name().c_str());

    VLOG(1) << "\tMaster: " << master;
    VLOG(1) << "\tFramework Name: " << *framework.mutable_name();
    VLOG(1) << "\tFramework User: " << *framework.mutable_user();
    VLOG(1) << "\tFramework Role: " << *framework.mutable_role();

#ifndef CV_0_24_1
    pthread_mutexattr_t attr;
    pthread_mutexattr_init(&attr);
    pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_RECURSIVE);
    pthread_mutex_init(&mutex, &attr);
    pthread_mutexattr_destroy(&attr);
    pthread_cond_init(&cond, 0);
#endif
    // See FrameWorkInfo in include/mesos/mesos.proto:
    if (framework.user().empty()) {
        Result<string> user = os::user();
        CHECK_SOME(user);

        framework.set_user(user.get());
    }

    CHECK(process == NULL);

    url = master;
    VLOG(1) << "MesosSchedulerDriver::MesosSchedulerDriver(): created 1 to be deprecated";
}


MesosSchedulerDriver::MesosSchedulerDriver(
    Scheduler* _scheduler,
    const FrameworkInfo& _framework,
    const string& _master,
    bool _implicitAcknowlegements,
    const Credential& _credential):
      detector(NULL),    
      scheduler(_scheduler),
      framework(_framework),
      master(_master),
      process(NULL),
      status(DRIVER_NOT_STARTED),
      implicitAcknowlegements(_implicitAcknowlegements),
      credential(new Credential(_credential))
{
    GOOGLE_PROTOBUF_VERIFY_VERSION;
#ifndef CV_0_24_1
    pthread_mutexattr_t attr;
    pthread_mutexattr_init(&attr);
    pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_RECURSIVE);
    pthread_mutex_init(&mutex, &attr);
    pthread_mutexattr_destroy(&attr);
    pthread_cond_init(&cond, 0);
#endif
    // See FrameWorkInfo in include/mesos/mesos.proto:
    if (framework.user().empty()) {
        Result<string> user = os::user();
        CHECK_SOME(user);
        framework.set_user(user.get());
    }

    CHECK(process == NULL);

    url = master;
    VLOG(1) << "MesosSchedulerDriver::MesosSchedulerDriver(): 2 end: status=" << status;
}


// duplicated from above but without implicitAcknowlegements in order
// to be easily removable as deprecated in the future
MesosSchedulerDriver::MesosSchedulerDriver(
    Scheduler* _scheduler,
    const FrameworkInfo& _framework,
    const string& _master,
    const Credential& _credential):
      detector(NULL),    
      scheduler(_scheduler),
      framework(_framework),
      master(_master),
      process(NULL),
      status(DRIVER_NOT_STARTED),
      implicitAcknowlegements(true),
      credential(new Credential(_credential))
{
    GOOGLE_PROTOBUF_VERIFY_VERSION;
#ifndef CV_0_24_1
    pthread_mutexattr_t attr;
    pthread_mutexattr_init(&attr);
    pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_RECURSIVE);
    pthread_mutex_init(&mutex, &attr);
    pthread_mutexattr_destroy(&attr);
    pthread_cond_init(&cond, 0);
#endif
    // See FrameWorkInfo in include/mesos/mesos.proto:
    if (framework.user().empty()) {
        Result<string> user = os::user();
        CHECK_SOME(user);

        framework.set_user(user.get());
    }

    CHECK(process == NULL);

    url = master;
    VLOG(1) << "MesosSchedulerDriver::MesosSchedulerDriver(): created 2 to be deprecated";
}


MesosSchedulerDriver::~MesosSchedulerDriver()
{
    VLOG(1) << "MesosSchedulerDriver::~MesosSchedulerDriver(): status=" << status;
    if (process != NULL) {
        delete process;
        process = NULL;
    }

    if (credential != NULL) {
        delete credential;
        credential = NULL;
    }

#ifndef CV_0_24_1
    pthread_mutex_destroy(&mutex);
    pthread_cond_destroy(&cond);
#endif
    VLOG(1) << "MesosSchedulerDriver::~MesosSchedulerDriver(): end: status=" << status;
}


Status MesosSchedulerDriver::start()
{
    VLOG(1) << "MesosSchedulerDriver::start(): status=" << status;
#ifdef CV_0_24_1
    std::lock_guard<sch_mutex> lock(mutex);
#else
    mesos::internal::Lock lock(&mutex);
#endif
    if (status != DRIVER_NOT_STARTED) {
        VLOG(1) << "MesosSchedulerDriver::start(): already running";
        if (status == DRIVER_STOPPED) {
            VLOG(1) << "MesosSchedulerDriver::start(): was stopped, starting registration";
            process->startRegistration();
        }
        status = DRIVER_RUNNING;
        return status;
    }

    CHECK(process == NULL);

    process = new UrbSchedulerProcess(this, scheduler, framework, master);
    process->startRegistration();
    status = DRIVER_RUNNING;
    VLOG(1) << "MesosSchedulerDriver::start(): end: status=" << status;
    return status;
}


Status MesosSchedulerDriver::stop(bool failover)
{
    VLOG(1) << "MesosSchedulerDriver::stop(): failover=" << failover << ", status=" << status;
#ifdef CV_0_24_1
    std::unique_lock<sch_mutex> lock(mutex);
#else
    mesos::internal::Lock lock(&mutex);
#endif
    bool aborted = false;
    if (status == DRIVER_RUNNING || status == DRIVER_ABORTED) {
        VLOG(1) << "MesosSchedulerDriver::stop(): signalling and calling process->stop()";
#ifdef CV_0_24_1
        cond.notify_one();
#else
        pthread_cond_signal(&cond);
#endif
        process->stop(failover);
        aborted = (status == DRIVER_ABORTED);
        status = DRIVER_STOPPED;
    }
    VLOG(1) << "MesosSchedulerDriver::stop(): end: status=" << status << ", aborted=" << aborted;
    return aborted ? DRIVER_ABORTED : status;
}


Status MesosSchedulerDriver::abort()
{
    VLOG(1) << "MesosSchedulerDriver::abort(): status=" << status;
#ifdef CV_0_24_1
    std::unique_lock<sch_mutex> lock(mutex);
#else
    mesos::internal::Lock lock(&mutex);
#endif
    if (status == DRIVER_RUNNING) {
        VLOG(1) << "MesosSchedulerDriver::abort(): calling process->abort(), signalling";
        CHECK(process != NULL);
        process->abort();
#ifdef CV_0_24_1
        cond.notify_one();
#else
        pthread_cond_signal(&cond);
#endif
        status = DRIVER_ABORTED;
    }
    VLOG(1) << "MesosSchedulerDriver::abort(): end: status=" << status;
    return status;
}


Status MesosSchedulerDriver::join()
{
    VLOG(1) << "MesosSchedulerDriver::join(): status=" << status;
#ifdef CV_0_24_1
    std::unique_lock<sch_mutex> lock(mutex);
#else
    mesos::internal::Lock lock(&mutex);
#endif
    if (status == DRIVER_RUNNING) {
        while (status == DRIVER_RUNNING) {
            VLOG(1) << "Driver join waiting on CV: status=" << status;
#ifdef CV_0_24_1
            cond.wait(lock);
#else
            pthread_cond_wait(&cond, &mutex);
#endif
        }
        CHECK(status == DRIVER_ABORTED || status == DRIVER_STOPPED);
    }
    VLOG(1) << "MesosSchedulerDriver::join(): end: status=" << status;
    return status;
}


Status MesosSchedulerDriver::run()
{
    VLOG(1) << "MesosSchedulerDriver::run()";
    Status status = start();
    status = status != DRIVER_RUNNING ? status : join();
    VLOG(1) << "MesosSchedulerDriver::run(): end: status=" << status;
    return status;
}


Status MesosSchedulerDriver::killTask(const TaskID& taskId)
{
    VLOG(1) << "MesosSchedulerDriver::killTask(): status=" << status;
#ifdef CV_0_24_1
    std::lock_guard<sch_mutex> lock(mutex);
#else
    mesos::internal::Lock lock(&mutex);
#endif
    if(status == DRIVER_RUNNING) {
        VLOG(1) << "MesosSchedulerDriver::killTask(): calling process->killTask()";
        CHECK(process != NULL);
        process->killTask(taskId);
    }
    VLOG(1) << "MesosSchedulerDriver::killTask(): end: status=" << status;
    return status;
}


Status MesosSchedulerDriver::launchTasks(
    const OfferID& offerId,
    const vector<TaskInfo>& tasks,
    const Filters& filters)
{
    VLOG(1) << "MesosSchedulerDriver::launchTasks(): status=" << status;
    vector<OfferID> offerIds;
    offerIds.push_back(offerId);

    Status status = launchTasks(offerIds, tasks, filters);
    VLOG(1) << "MesosSchedulerDriver::launchTasks(): 1 end: status=" << status;
    return status;
}


Status MesosSchedulerDriver::launchTasks(
    const vector<OfferID>& offerIds,
    const vector<TaskInfo>& tasks,
    const Filters& filters)
{
    VLOG(1) << "MesosSchedulerDriver::launchTasks(): status=" << status;
#ifdef CV_0_24_1
    std::lock_guard<sch_mutex> lock(mutex);
#else
    mesos::internal::Lock lock(&mutex);
#endif
    VLOG(1) << "TaskInfo size: " << tasks.size() << "\n";
    VLOG(1) << "OfferIds size: " << offerIds.size() << "\n";
    VLOG(1) << "Filters: [" << filters.DebugString() << "]\n";
    if (status == DRIVER_RUNNING) {
        VLOG(1) << "MesosSchedulerDriver::launchTasks(): calling process->launchTasks()";
        CHECK(process != NULL);
        process->launchTasks(offerIds,tasks,filters);
    }
    VLOG(1) << "MesosSchedulerDriver::launchTasks(): 2 end: status=" << status;
    return status;
}


Status MesosSchedulerDriver::acceptOffers(
      const std::vector<OfferID>& offerIds,
      const std::vector<Offer::Operation>& operations,
      const Filters& filters)
{
    VLOG(1) << "MesosSchedulerDriver::acceptOffers(): status=" << status;
#ifdef CV_0_24_1
    std::lock_guard<sch_mutex> lock(mutex);
#else
    mesos::internal::Lock lock(&mutex);
#endif
    if (status == DRIVER_RUNNING) {
        VLOG(1) << "MesosSchedulerDriver::acceptOffers(): calling process->acceptOffers()";
        process->acceptOffers(offerIds, operations, filters);
    }
    VLOG(1) << "MesosSchedulerDriver::acceptOffers(): end: status=" << status;
    return status;
}


Status MesosSchedulerDriver::declineOffer(
    const OfferID& offerId,
    const Filters& filters)
{
    VLOG(1) << "MesosSchedulerDriver::declineOffer(): status=" << status;
    vector<OfferID> offerIds;
    offerIds.push_back(offerId);

    Status status = launchTasks(offerIds, vector<TaskInfo>(), filters);
    VLOG(1) << "MesosSchedulerDriver::declineOffer(): end: status=" << status;
    return status;
}


Status MesosSchedulerDriver::reviveOffers()
{
    VLOG(1) << "MesosSchedulerDriver::reviveOffers(): status=" << status;
#ifdef CV_0_24_1
    std::lock_guard<sch_mutex> lock(mutex);
#else
    mesos::internal::Lock lock(&mutex);
#endif
    if (status == DRIVER_RUNNING) {
        VLOG(1) << "MesosSchedulerDriver::reviveOffers(): calling process->reviveOffers()";
        CHECK(process != NULL);
        process->reviveOffers();
    }
    VLOG(1) << "MesosSchedulerDriver::reviveOffers(): end: status=" << status;
    return status;
}

Status MesosSchedulerDriver::suppressOffers()
{
    VLOG(1) << "MesosSchedulerDriver::suppressOffers(): status=" << status;
#ifdef CV_0_24_1
    std::lock_guard<sch_mutex> lock(mutex);
#else
    mesos::internal::Lock lock(&mutex);
#endif
    if (status != DRIVER_RUNNING) {
        VLOG(1) << "MesosSchedulerDriver::suppressOffers(): not running";
        return status;
    }

    CHECK(process != NULL);
    LOG(WARNING) << "suppressOffers is not implemented";
    return status;
}


Status MesosSchedulerDriver::acknowledgeStatusUpdate(
      const TaskStatus& st)
{
    VLOG(1) << "MesosSchedulerDriver::acknowledgeStatusUpdate(): status=" << status;
#ifdef CV_0_24_1
    std::lock_guard<sch_mutex> lock(mutex);
#else
    mesos::internal::Lock lock(&mutex);
#endif
    if (status == DRIVER_RUNNING) {
        VLOG(1) << "MesosSchedulerDriver::acknowledgeStatusUpdate(): calling process->acknowledgeStatusUpdate()";
        CHECK(process != NULL);
        process->acknowledgeStatusUpdate(st);
    }
    VLOG(1) << "MesosSchedulerDriver::acknowledgeStatusUpdate(): end: status=" << status;
    return status;
}


Status MesosSchedulerDriver::sendFrameworkMessage(
    const ExecutorID& executorId,
    const SlaveID& slaveId,
    const string& data)
{
    VLOG(1) << "MesosSchedulerDriver::sendFrameworkMessage(): status=" << status;
#ifdef CV_0_24_1
    std::lock_guard<sch_mutex> lock(mutex);
#else
    mesos::internal::Lock lock(&mutex);
#endif
    if (status == DRIVER_RUNNING) {
        VLOG(1) << "MesosSchedulerDriver::sendFrameworkMessage(): calling process->sendFrameworkMessage()";
        CHECK(process != NULL);
        process->sendFrameworkMessage(
           executorId, slaveId, data);
    }
    VLOG(1) << "MesosSchedulerDriver::sendFrameworkMessage(): end: status=" << status;
    return status;
}


Status MesosSchedulerDriver::reconcileTasks(
    const vector<TaskStatus>& statuses)
{
    VLOG(1) << "MesosSchedulerDriver::reconcileTasks(): status=" << status;
#ifdef CV_0_24_1
    std::lock_guard<sch_mutex> lock(mutex);
#else
    mesos::internal::Lock lock(&mutex);
#endif
    if (status == DRIVER_RUNNING) {
        VLOG(1) << "MesosSchedulerDriver::reconcileTasks(): calling process->reconcileTasks()";
        CHECK(process != NULL);
        process->reconcileTasks(statuses);
    }
    VLOG(1) << "MesosSchedulerDriver::reconcileTasks(): end: status=" << status;
    return status;
}


Status MesosSchedulerDriver::requestResources(
    const vector<Request>& requests)
{
    VLOG(1) << "MesosSchedulerDriver::requestResources(): status=" << status;
#ifdef CV_0_24_1
    std::lock_guard<sch_mutex> lock(mutex);
#else
    mesos::internal::Lock lock(&mutex);
#endif
    if (status == DRIVER_RUNNING) {
        VLOG(1) << "MesosSchedulerDriver::requestResources(): calling process->requestResources()";
        CHECK(process != NULL);
        process->requestResources(requests);
    }
    VLOG(1) << "MesosSchedulerDriver::requestResources(): end: status=" << status;
    return status;
}

