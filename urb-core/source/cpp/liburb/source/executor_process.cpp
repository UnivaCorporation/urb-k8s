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


#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <uuid/uuid.h>

#include <arpa/inet.h>

#include <iostream>
#include <map>
#include <string>
#include <sstream>
#include <vector>

#include <glog/logging.h>

#include <mesos/executor.hpp>
#include <mesos.pb.h>
#include <messages.pb.h>

#include <stout/linkedhashmap.hpp>
#include <stout/os.hpp>

#include "timer.hpp"
#include <json_protobuf.h>
#include <message_broker.hpp>
#include <executor_process.hpp>


using namespace mesos;

using std::map;
using std::string;
using std::vector;


// Implementation of C++ API.


namespace mesos {
namespace internal {
const std::string ExecutorProcess::REGISTER_EXECUTOR_TARGET = "RegisterExecutorMessage";
const std::string ExecutorProcess::REREGISTER_EXECUTOR_TARGET = "ReregisterExecutorMessage";
const std::string ExecutorProcess::STATUS_UPDATE_TARGET = "StatusUpdateMessage";
const std::string ExecutorProcess::EXECUTOR_TO_FRAMEWORK_TARGET = "ExecutorToFrameworkMessage";
}
}

ExecutorNotifyCallback::ExecutorNotifyCallback(UrbExecutorProcess* process) :pProcess(process) {
    messages["ExecutorRegisteredMessage"] = EXECUTOR_REGISTERED;
    messages["RunTaskMessage"] = RUN_TASK;
    messages["KillTaskMessage"] = KILL_TASK;
    messages["FrameworkToExecutorMessage"] = FRAMEWORK_TO_EXECUTOR;
    messages["ShutdownExecutorMessage"] = SHUTDOWN_EXECUTOR;
    messages["ExecutorReregisteredMessage"] = EXECUTOR_REREGISTERED;
    messages["ReconnectExecutorMessage"] = RECONNECT_EXECUTOR;
    messages["ServiceDisconnectedMessage"] = SERVICE_DISCONNECTED;
    messages["StatusUpdateAcknowledgementMessage"] = STATUS_UPDATE_ACKNOWLEDGE;
}

void ExecutorNotifyCallback::onInput(liburb::message_broker::Channel& channel, liburb::message_broker::Message& message) {
    std::map<std::string,Messages>::iterator it = messages.find(message.getTarget());
    if(it == messages.end()) {
        LOG(ERROR) << "Received unknown message: " << message.getPayloadAsString()
                   << ", (type: " << message.getTypeStr()
                   << "), (target: " << message.getTarget()
                   << "), (sourceId: " << message.getSourceId()
                   << "), (replyTo:" << message.getReplyTo()
                   << "), (channel:" << channel.getName() << ")";
        return;
    }
    switch(it->second) {
        case EXECUTOR_REGISTERED:
            {
                mesos::internal::ExecutorRegisteredMessage payload;
                json_protobuf::update_from_json(message.getPayloadAsJson(),payload);
                pProcess->registered(payload.executor_info(),
                    payload.framework_id(),
                    payload.framework_info(),
                    payload.slave_id(),
                    payload.slave_info());
           }
           break;
        case EXECUTOR_REREGISTERED:
            {
                mesos::internal::ExecutorReregisteredMessage payload;
                json_protobuf::update_from_json(message.getPayloadAsJson(),payload);
                pProcess->reregistered(
                    payload.slave_id(),
                    payload.slave_info());
           }
           break;
        case RECONNECT_EXECUTOR:
            {
                mesos::internal::ReconnectExecutorMessage payload;
                json_protobuf::update_from_json(message.getPayloadAsJson(),payload);
                pProcess->reconnect(message.getSourceId(),
                    payload.slave_id());
           }
           break;
        case SERVICE_DISCONNECTED:
           {
                UPID from;
                pProcess->reconnect(from,pProcess->slaveId_);
           }
           break;
        case STATUS_UPDATE_ACKNOWLEDGE:
            {
                mesos::internal::StatusUpdateAcknowledgementMessage payload;
                json_protobuf::update_from_json(message.getPayloadAsJson(),payload);
                pProcess->statusUpdateAcknowledgement(payload.slave_id(),
                         payload.framework_id(),
                         payload.task_id(),
                         payload.uuid());
           }
           break;
       case KILL_TASK:
            {
                mesos::internal::KillTaskMessage payload;
                json_protobuf::update_from_json(message.getPayloadAsJson(),payload);
                pProcess->killTask(payload.task_id());
            }
            break;
       case RUN_TASK:
            {
                mesos::internal::RunTaskMessage payload;
                json_protobuf::update_from_json(message.getPayloadAsJson(),payload);
                pProcess->runTask(payload.task());
            }
            break;
       case FRAMEWORK_TO_EXECUTOR:
            {
                mesos::internal::FrameworkToExecutorMessage payload;
                json_protobuf::update_from_json(message.getPayloadAsJson(),payload);
                pProcess->frameworkMessage(payload.slave_id(),
                          payload.framework_id(),
                          payload.executor_id(),
                          payload.data());
            }
        break;
       case SHUTDOWN_EXECUTOR:
            {
                mesos::internal::ShutdownExecutorMessage payload;
                json_protobuf::update_from_json(message.getPayloadAsJson(),payload);
                pProcess->shutdown();
            }
        break;
       default:
           LOG(INFO) << "Received unsupported message: " << message.getTarget();
           break;
    }
}


UrbExecutorProcess::UrbExecutorProcess(MesosExecutorDriver *pDriver,
            Executor *pExecutor,
            const FrameworkID& frameworkId,
            const ExecutorID& executorId,
            const SlaveID& slaveId) :
        pDriver_(pDriver),
        pExecutor_(pExecutor),
        frameworkId_(frameworkId),
        executorId_(executorId),
        slaveId_(slaveId),
        notifyCallback_(std::make_shared<ExecutorNotifyCallback>(this)),
        pBroker_(liburb::message_broker::MessageBroker::getInstance()),
        registrationTimer_(this),
        channelsCreated_(false),
        aborted_(false),
        connected_(false) {
}

void UrbExecutorProcess::createChannels(SlaveID slaveId) {
    if (!channelsCreated_) {
        pNotifyChannel_ = getBroker()->createChannel("notify");
        channelsCreated_ = true;
    }
    pNotifyChannel_->registerInputCallback(notifyCallback_);
    slaveId_ = slaveId;
}

UrbExecutorProcess::~UrbExecutorProcess() {
    if(channelsCreated_) {
        VLOG(1) << "Deleteing notify channel";
        pBroker_->shutdown();
        VLOG(1) << "Waiting for loop shutdown";
        liburb::EvHelper& ev = liburb::EvHelper::getInstance();
        while(!ev.isLoopExited()) {
            sleep(1);
        }
        VLOG(1) << "Broker shutdown";
    }
}

std::shared_ptr<liburb::message_broker::MessageBroker> UrbExecutorProcess::getBroker() {
    return pBroker_;
}

void UrbExecutorProcess::setPayload(const google::protobuf::Message& gmessage,
                                    liburb::message_broker::Message& message) {
    Json::Value json;
    json_protobuf::convert_to_json(gmessage, json);
    message.getPayloadAsJson()[gmessage.GetTypeName()] = json;
}

void UrbExecutorProcess::sendMesosMessage(google::protobuf::Message& message,
        const std::string& target) {
    liburb::message_broker::Message m;
    m.setTarget(target);
    setPayload(message,m);
    pNotifyChannel_->write(m);
}


void UrbExecutorProcess::sendMessage(
    mesos::internal::StatusUpdateMessage& m) {
    sendMesosMessage(m,STATUS_UPDATE_TARGET);

}
void UrbExecutorProcess::sendMessage(
    mesos::internal::RegisterExecutorMessage& rem) {
    // This needs special handling... we must attach the slave channel
    // as the response channel
    liburb::message_broker::Message m;
    m.setTarget(REGISTER_EXECUTOR_TARGET);
    setPayload(rem,m);
    size_t pos = slaveId_.value().rfind(":");
    if (pos != std::string::npos) {
        std::string executorRunnerChannel = slaveId_.value().substr(pos+1);
        m.setReplyTo(executorRunnerChannel);
    }
    pNotifyChannel_->write(m);
}
void UrbExecutorProcess::sendMessage(
    mesos::internal::ReregisterExecutorMessage& rem) {
    // This needs special handling... we must attach the slave channel
    // as the response channel
    liburb::message_broker::Message m;
    m.setTarget(REREGISTER_EXECUTOR_TARGET);
    setPayload(rem,m);
    size_t pos = slaveId_.value().rfind(":");
    if (pos != std::string::npos) {
        std::string executorRunnerChannel = slaveId_.value().substr(pos+1);
        m.setReplyTo(executorRunnerChannel);
    }
    pNotifyChannel_->write(m);
}
void UrbExecutorProcess::sendMessage(
    mesos::internal::ExecutorToFrameworkMessage& m) {
    sendMesosMessage(m,EXECUTOR_TO_FRAMEWORK_TARGET);
}

void UrbExecutorProcess::startRegistration() {
    registrationTimer_.delay(Seconds(0), &UrbExecutorProcess::doReliableRegistration);
}

void UrbExecutorProcess::doReliableRegistration() {
    LOG(INFO) << "In reliable Registration\n";
    const Option<std::string> master(os::getenv("URB_MASTER"));
    if (master.isNone()) {
        LOG(ERROR) << "UrbExecutorProcess::doReliableRegistration: URB_MASTER not defined";
        return;
    }

    VLOG(1) << "Sending registration request to " << master.get()
            << " with executor id=" << executorId_.value()
            << ", framework id=" << frameworkId_.value();

    try {
        getBroker()->setUrl(master.get());
        createChannels(slaveId_);
        mesos::internal::RegisterExecutorMessage message;
        message.mutable_framework_id()->MergeFrom(frameworkId_);
        message.mutable_executor_id()->MergeFrom(executorId_);
        sendMessage(message);
    } catch (std::exception& e) {
        // TODO: URB... Should we send more messages to redis?
        LOG(INFO) << "Scheduling registration delay, exception: " << e.what();
        registrationTimer_.delay(Seconds(1), &UrbExecutorProcess::doReliableRegistration);
    }
}

//Our supported actions
void UrbExecutorProcess::registered(const ExecutorInfo& executorInfo,
                const FrameworkID& /*frameworkId*/,
                const FrameworkInfo& frameworkInfo,
                const SlaveID& slaveId,
                const SlaveInfo& slaveInfo){
    if (aborted_) {
      VLOG(1) << "Ignoring registered message from slave " << slaveId.value()
              << " because the driver is aborted!";
      return;
    }

    LOG(INFO) << "Executor registered on slave " << slaveId.value()
              << " with executor id=" << executorInfo.executor_id().value();

    connected_ = true;

    // Start our heartbeat
    startHeartbeat();
    pExecutor_->registered(pDriver_, executorInfo, frameworkInfo, slaveInfo);
}

void UrbExecutorProcess::startHeartbeat() {
    Json::Value heartbeatMessage;
    heartbeatMessage["channel_info"] = Json::Value();
    heartbeatMessage["channel_info"]["channel_id"] = pNotifyChannel_->getName();
    heartbeatMessage["channel_info"]["framework_id"] = frameworkId_.value();
    heartbeatMessage["channel_info"]["slave_id"] = slaveId_.value();
    heartbeatMessage["channel_info"]["endpoint_type"] = "executor";
    heartbeatMessage["channel_info"]["executor_id"] = executorId_.value();
    pNotifyChannel_->setHeartbeatPayload(heartbeatMessage);
}

void UrbExecutorProcess::reregistered(const SlaveID& slaveId, const SlaveInfo& slaveInfo){
    if (aborted_) {
      VLOG(1) << "Ignoring re-registered message from slave " << slaveId.value()
              << " because the driver is aborted!";
      return;
    }

    LOG(INFO) << "Executor re-registered on slave " << slaveId.value();

    connected_ = true;

    startHeartbeat();
    pExecutor_->reregistered(pDriver_, slaveInfo);
}

void UrbExecutorProcess::reconnect(const UPID& /*from*/, const SlaveID& slaveId)
{
    if (aborted_) {
      VLOG(1) << "Ignoring reconnect message from slave " << slaveId.value()
              << " because the driver is aborted!";
      return;
    }

    LOG(INFO) << "Received reconnect request from slave " << slaveId.value();

    // Update the slave link.
    //slave = from;

    // Re-register with slave.
    mesos::internal::ReregisterExecutorMessage message;
    message.mutable_executor_id()->MergeFrom(executorId_);
    message.mutable_framework_id()->MergeFrom(frameworkId_);

    // Send all unacknowledged updates.
    for (const mesos::internal::StatusUpdate& update: updates.values()) {
      message.add_updates()->MergeFrom(update);
    }

    // Send all unacknowledged tasks.
    for (const TaskInfo& task: tasks_.values()) {
      message.add_tasks()->MergeFrom(task);
    }

    sendMessage(message);
}

void UrbExecutorProcess::runTask(const TaskInfo& task) {
    if (aborted_) {
      VLOG(1) << "Ignoring run task message for task " << task.task_id().value()
              << " because the driver is aborted!";
      return;
    }

    if (!connected_) {
      VLOG(1) << "Ignoring run task message for task " << task.task_id().value()
              << " because the driver is disconnected!";
      return;
    }

    CHECK(!tasks_.contains(task.task_id().value()))
      << "Unexpected duplicate task " << task.task_id().value();

    tasks_[task.task_id().value()] = task;

    VLOG(1) << "Executor asked to run task '" << task.task_id().value() << "'";

    pExecutor_->launchTask(pDriver_, task);
}

void UrbExecutorProcess::killTask(const TaskID& taskId) {
    if (aborted_) {
      VLOG(1) << "Ignoring kill task message for task " << taskId.value()
              <<" because the driver is aborted!";
      return;
    }

    VLOG(1) << "Executor asked to kill task '" << taskId.value() << "'";

    pExecutor_->killTask(pDriver_, taskId);
}

void UrbExecutorProcess::statusUpdateAcknowledgement(
      const SlaveID& /*slaveId*/,
      const FrameworkID& frameworkId,
      const TaskID& taskId,
      const string& uuid) {
    if (aborted_) {
      VLOG(1) << "Ignoring status update acknowledgement "
              << " for task " << taskId.value()
              << " of framework " << frameworkId.value()
              << " because the driver is aborted!";
      return;
    }

    if (!connected_) {
      VLOG(1) << "Ignoring status update acknowledgement for task " << taskId.value()
              << " of framework " << frameworkId.value()
              << " because the driver is disconnected!";
      return;
    }

    LOG(INFO) << "Executor received status update acknowledgement "
              << " for task " << taskId.value()
              << " of framework " << frameworkId.value();

    bool eraseTasks = updates[uuid].status().state() == TASK_FINISHED;
    // Remove the corresponding update.
    updates.erase(uuid);

    // Remove the corresponding task.
    // URB Deviation... we only erase tasks when the complete
    if (eraseTasks) {
        tasks_.erase(taskId.value());
    }
}
void UrbExecutorProcess::frameworkMessage(const SlaveID& /*slaveId*/,
                      const FrameworkID& /*frameworkId*/,
                      const ExecutorID& /*executorId*/,
                      const string& data) {
    if (aborted_) {
      VLOG(1) << "Ignoring framework message because the driver is aborted!";
      return;
    }

    if (!connected_) {
      VLOG(1) << "Ignoring framework message because the driver is disconnected!";
      return;
    }

    VLOG(1) << "Executor received framework message";

    pExecutor_->frameworkMessage(pDriver_, data);
}

void UrbExecutorProcess::shutdown() {
    if (aborted_) {
      VLOG(1) << "Ignoring shutdown message because the driver is aborted!";
      return;
    }

    LOG(INFO) << "Executor asked to shutdown";

    /* URB Necessary logic */
    int masterPid = getpid();
    int pid = fork();
    if (pid != 0) {
        VLOG(1) << "UrbExecutorProcess::shutdown: parent: pid=" << pid << ", masterPid=" << masterPid;
        VLOG(1) << "UrbExecutorProcess::shutdown: parent: call executor shutdown";
        pExecutor_->shutdown(pDriver_);
        //Shutdown the message bus as well
        VLOG(1) << "UrbExecutorProcess::shutdown: parent: call broker shutdown";
        pBroker_->shutdown();
    } else {
        VLOG(1) << "UrbExecutorProcess::shutdown: child: pid=" << pid << ", masterPid=" << masterPid;
        sleep(1);
        VLOG(1) << "UrbExecutorProcess::shutdown: child: slept a sec, send kill signal to master with pid=" << masterPid;
        kill(masterPid, SIGKILL);
        // The signal might not get delivered immediately, so sleep for a
        // few seconds. Worst case scenario, exit abnormally.
        VLOG(1) << "UrbExecutorProcess::shutdown: child: sleep for 5 sec";
        sleep(5);
        VLOG(1) << "UrbExecutorProcess::shutdown: child: slept, exit -1";
        exit(-1);
    }

    /* End URB Logic */
    LOG(INFO) << "UrbExecutorProcess::shutdown: end";
    aborted_ = true; // To make sure not to accept any new messages.
}

void UrbExecutorProcess::stop() {
    // TODO: URB: make sure this is OK
    // The driver does everything that is necessary for URB
    LOG(INFO) << "UrbExecutorProcess::stop: dummy";
}

void UrbExecutorProcess::abort() {
    LOG(INFO) << "UrbExecutorProcess::abort: Deactivating the executor urb callback";
    aborted_ = true;
    CHECK(aborted_);
   // The driver does everything that is necessary for URB
}

void UrbExecutorProcess::sendStatusUpdate(const TaskStatus& status) {
    if (status.state() == TASK_STAGING) {
      LOG(ERROR) << "Executor is not allowed to send "
                 << "TASK_STAGING status update. Aborting!";
      pDriver_->abort();
      pExecutor_->error(pDriver_, "Attempted to send TASK_STAGING status update");
      return;
    }

    mesos::internal::StatusUpdateMessage message;
    mesos::internal::StatusUpdate* update = message.mutable_update();
    update->mutable_framework_id()->MergeFrom(frameworkId_);
    update->mutable_executor_id()->MergeFrom(executorId_);
    update->mutable_slave_id()->MergeFrom(slaveId_);
    update->mutable_status()->MergeFrom(status);
    update->set_timestamp(time(0));
    update->mutable_status()->set_timestamp(update->timestamp());

    /* Generate a UUID */
    uuid_t uuid;
    uuid_generate(uuid);
    update->set_uuid((char*)uuid);
    //message.set_pid(self());

    // Incoming status update might come from an executor which has not set
    // slave id in TaskStatus. Set/overwrite slave id.
    update->mutable_status()->mutable_slave_id()->CopyFrom(slaveId_);

    // Capture the status update.
    updates[update->uuid()] = *update;

    sendMessage(message);
}

void UrbExecutorProcess::sendFrameworkMessage(const string& data) {
    mesos::internal::ExecutorToFrameworkMessage message;
    message.mutable_slave_id()->MergeFrom(slaveId_);
    message.mutable_framework_id()->MergeFrom(frameworkId_);
    message.mutable_executor_id()->MergeFrom(executorId_);
    message.set_data(data);
    sendMessage(message);
}
