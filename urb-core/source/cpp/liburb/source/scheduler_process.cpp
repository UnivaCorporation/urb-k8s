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
#include <uuid/uuid.h>

#include <arpa/inet.h>

#include <iostream>
#include <map>
#include <string>
#include <sstream>
#include <vector>

#include <glog/logging.h>

#include <mesos/scheduler.hpp>
#include <mesos.pb.h>
#include <messages.pb.h>
//#include <common/lock.hpp>
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

namespace mesos {
namespace internal {
const std::string SchedulerProcess::REGISTER_FRAMEWORK_TARGET = "RegisterFrameworkMessage";
const std::string SchedulerProcess::REREGISTER_FRAMEWORK_TARGET = "ReregisterFrameworkMessage";
const std::string SchedulerProcess::STATUS_UPDATE_ACKNOWLEDGEMENT_TARGET = "StatusUpdateAcknowledgementMessage";
const std::string SchedulerProcess::UNREGISTER_FRAMEWORK_TARGET = "UnregisterFrameworkMessage";
const std::string SchedulerProcess::DEACTIVATE_FRAMEWORK_TARGET = "DeactivateFrameworkMessage";
const std::string SchedulerProcess::KILL_TASK_TARGET = "KillTaskMessage";
const std::string SchedulerProcess::RESOURCE_REQUEST_TARGET = "ResourceRequestMessage";
const std::string SchedulerProcess::LAUNCH_TASKS_TARGET = "LaunchTasksMessage";
const std::string SchedulerProcess::REVIVE_OFFERS_TARGET = "ReviveOffersMessage";
//const std::string SchedulerProcess::SUPPRESS_OFFERS_TARGET = "SuppressOffersMessage";
const std::string SchedulerProcess::FRAMEWORK_TO_EXECUTOR_TARGET = "FrameworkToExecutorMessage";
const std::string SchedulerProcess::RECONCILE_TASKS_TARGET = "ReconcileTasksMessage";
}
}

SchedulerNotifyCallback::SchedulerNotifyCallback(UrbSchedulerProcess* process) :pProcess_(process) {
}

void SchedulerNotifyCallback::onInput(liburb::message_broker::Channel& channel, liburb::message_broker::Message& message) {
    // First we need to check for an error... this indicates a loss of connection to the broker
    if (message.getType() == liburb::message_broker::Message::Type::ERROR) {
        LOG(ERROR) << "Lost connection with message broker detected";
        pProcess_->connected_ = false;
        pProcess_->startRegistration();
        return;
    }
    std::map<std::string,Messages>::iterator it = messages_.find(message.getTarget());
    if (it == messages_.end()) {
        LOG(ERROR) << "SchedulerNotifyCallback::onInput(): Received unknown message: " << message.getPayloadAsString()
                   << ", (type: " << message.getTypeStr()
                   << "), (target: " << message.getTarget()
                   << "), (sourceId: " << message.getSourceId()
                   << "), (replyTo:" << message.getReplyTo()
                   << "), (channel:" << channel.getName() << ")";
        return;
    }
    switch(it->second) {
        case FRAMEWORK_REGISTERED:
            {
                VLOG(2) << "SchedulerNotifyCallback::onInput(): FRAMEWORK_REGISTERED";
                mesos::internal::FrameworkRegisteredMessage payload;
                json_protobuf::update_from_json(message.getPayloadAsJson(),payload);
                pProcess_->registered(pProcess_->master_,
                                     payload.framework_id(),
                                     payload.master_info());
            }
            break;
        case FRAMEWORK_REREGISTERED:
            {
                VLOG(2) << "SchedulerNotifyCallback::onInput(): FRAMEWORK_REREGISTERED";
                mesos::internal::FrameworkReregisteredMessage payload;
                json_protobuf::update_from_json(message.getPayloadAsJson(),payload);
                pProcess_->reregistered(pProcess_->master_,
                                     payload.framework_id(),
                                     payload.master_info());
            }
            break;
        case FRAMEWORK_ERROR:
            {
                VLOG(2) << "SchedulerNotifyCallback::onInput(): FRAMEWORK_ERROR";
                mesos::internal::FrameworkErrorMessage payload;
                json_protobuf::update_from_json(message.getPayloadAsJson(),payload);
                pProcess_->error(payload.message());
            }
            break;
        case LOST_SLAVE:
            {
                VLOG(2) << "SchedulerNotifyCallback::onInput(): LOST_SLAVE";
                mesos::internal::LostSlaveMessage payload;
                json_protobuf::update_from_json(message.getPayloadAsJson(),payload);
                pProcess_->lostSlave(pProcess_->master_, payload.slave_id());
            }
            break;
        case RESCIND_RESOURCE_OFFER:
            {
                VLOG(2) << "SchedulerNotifyCallback::onInput(): RESCIND_RESOURCE_OFFER";
                mesos::internal::RescindResourceOfferMessage payload;
                json_protobuf::update_from_json(message.getPayloadAsJson(),payload);
                pProcess_->rescindOffer(pProcess_->master_,
                                     payload.offer_id());
            }
            break;
        case RESOURCE_OFFERS:
            {
                VLOG(2) << "SchedulerNotifyCallback::onInput(): RESOURCE_OFFERS";
                mesos::internal::ResourceOffersMessage payload;
                json_protobuf::update_from_json(message.getPayloadAsJson(),payload);
                std::vector<Offer> offerVector;
                std::vector<std::string> pidVector;
                int i;
                for(i=0; i < payload.offers_size(); i++) {
                    Offer offer = payload.offers(i);
                    offerVector.push_back(offer);
                }
                for(i=0; i < payload.pids_size(); i++) {
                    std::string pid = payload.pids(i);
                    pidVector.push_back(pid);
                }

                pProcess_->resourceOffers(pProcess_->master_,
                                     offerVector,
                                     pidVector);
            }
            break;
        case EXECUTOR_TO_FRAMEWORK:
            {
                VLOG(2) << "SchedulerNotifyCallback::onInput(): EXECUTOR_TO_FRAMEWORK";
                mesos::internal::ExecutorToFrameworkMessage payload;
                json_protobuf::update_from_json(message.getPayloadAsJson(),payload);
                pProcess_->frameworkMessage(payload.slave_id(),
                                     payload.framework_id(),
                                     payload.executor_id(),
                                     payload.data());
            }
            break;
        case STATUS_UPDATE:
            {
                VLOG(2) << "SchedulerNotifyCallback::onInput(): STATUS_UPDATE";
                mesos::internal::StatusUpdateMessage payload;
                json_protobuf::update_from_json(message.getPayloadAsJson(),payload);
                pProcess_->statusUpdate(pProcess_->master_,
                                     payload.update(),
                                     payload.pid());
            }
            break;
        case SERVICE_DISCONNECTED:
            {
                VLOG(2) << "SchedulerNotifyCallback::onInput(): SERVICE_DISCONNECTED";
                //We still have a redis connection so just send a message...
                mesos::internal::ReregisterFrameworkMessage message;
                message.mutable_framework()->MergeFrom(pProcess_->framework_);
                message.set_failover(pProcess_->failover_);
                pProcess_->sendMessage(message);
            }
            break;

       default:
           LOG(INFO) << "SchedulerNotifyCallback::onInput(): Received unsupported message: " << message.getTarget();
           break;
    }
}


UrbSchedulerProcess::UrbSchedulerProcess(MesosSchedulerDriver* pDriver,
                        Scheduler* scheduler,
                        const FrameworkInfo& framework,
                        std::string master) :
      pBroker_(liburb::message_broker::MessageBroker::getInstance()),
      channelsCreated_(false),
      notifyCallback_(std::make_shared<SchedulerNotifyCallback>(this)),
      pDriver_(pDriver),
      pScheduler_(scheduler),
      framework_(framework),
      failover_(framework.has_id() && !framework.id().value().empty()),
      master_(master),
      connected_(false),
      aborted_(false),
      authenticated_(false),
      reauthenticate_(false),
      registrationTimer_(this),
      reconcileTimer_(this)
{
    VLOG(1) << "UrbSchedulerProcess::UrbSchedulerProcess(): this=" << this;
    VLOG(2) << "Framework name=" << framework_.name()
            << ", framework_id=" << (framework_.has_id() ? framework_.id().value() : "")
            << ", failover=" << failover_;
    reconcileTimer_.delay(Seconds(60), &UrbSchedulerProcess::checkReconcile);
}

void UrbSchedulerProcess::checkReconcile() {
    VLOG(1) << "UrbSchedulerProcess::checkReconcile(): this=" << this << ", connected=" << connected_ << ", aborted=" << aborted_;
    std::vector<TaskStatus> statuses;
    for(std::map<std::string,TaskState>::iterator iterator = activeTasks_.begin(); iterator != activeTasks_.end(); ++iterator) {
        if(iterator->second == TASK_STAGING) {
            //This could be a lost task... ask the master about it
            TaskStatus status;
            status.mutable_task_id()->set_value(iterator->first);
            status.set_state(TASK_STAGING);
            statuses.push_back(status);
        }
    }
    if(statuses.size() > 0) {
        //Send the message to the master
        reconcileTasks(statuses);
    }
    //Schedule again...
    reconcileTimer_.delay(Seconds(60), &UrbSchedulerProcess::checkReconcile);
}

void UrbSchedulerProcess::createChannels() {
    if(!channelsCreated_) {
        notifyChannel_ = getBroker()->createChannel("notify");
        channelsCreated_ = true;
    }
    notifyChannel_->registerInputCallback(notifyCallback_);
}

UrbSchedulerProcess::~UrbSchedulerProcess() {
    VLOG(1) << "UrbSchedulerProcess::~UrbSchedulerProcess(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    if(channelsCreated_) {
        LOG(INFO) << "Deleteing notify channel";
        pBroker_->shutdown();
        LOG(INFO) << "Waiting for loop shutdown";
        liburb::EvHelper& ev = liburb::EvHelper::getInstance();
        while(!ev.isLoopExited()) {
            VLOG(1) << "UrbSchedulerProcess::~UrbSchedulerProcess() waiting for exit";
            sleep(1);
        }
        LOG(INFO) << "Broker shutdown";
    }
}

std::shared_ptr<liburb::message_broker::MessageBroker> UrbSchedulerProcess::getBroker() {
    return pBroker_;
}

void UrbSchedulerProcess::setPayload(const google::protobuf::Message& gmessage,
                                     liburb::message_broker::Message& message) {
    Json::Value json;
    json_protobuf::convert_to_json(gmessage, json);
    VLOG(4) << "UrbSchedulerProcess::setPayload: " << json;
    message.getPayloadAsJson()[gmessage.GetTypeName()] = json;
}

// TODO: authentication
//void UrbSchedulerProcess::authenticate() {}
//void UrbSchedulerProcess::_authenticate() {}
//void UrbSchedulerProcess::authenticationTimeout(Future<bool> future) {}

void UrbSchedulerProcess::registered(
      const UPID& from,
      const FrameworkID& frameworkId_,
      const MasterInfo& masterInfo) {
    VLOG(1) << "UrbSchedulerProcess::registered(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    if (aborted_) {
      VLOG(1) << "Ignoring framework registered message because "
              << "the driver is not running!";
      return;
    }

    if (connected_) {
      VLOG(1) << "Ignoring framework registered message because "
              << "the driver is already connected!";
      return;
    }

    if (master_ != from) {
      LOG(WARNING)
        << "Ignoring framework registered message because it was sent "
        << "from '" << from << "' instead of the leading master '"
        << master_ << "'";
      return;
    }

    framework_.mutable_id()->MergeFrom(frameworkId_);

    LOG(INFO) << "Framework registered with " << framework_.id().value();

    connected_ = true;
    failover_ = false;

    // Start our heartbeat
    startHeartbeat(frameworkId_);

    pScheduler_->registered(pDriver_, frameworkId_, masterInfo);

    VLOG(1) << "UrbSchedulerProcess::registered() end: connected="
            << connected_ << ", aborted=" << aborted_;
}

void UrbSchedulerProcess::startHeartbeat(const FrameworkID& frameworkId) {
    VLOG(1) << "UrbSchedulerProcess::startHeartbeat(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    // Start our heartbeat
    Json::Value heartbeatMessage;
    heartbeatMessage["channel_info"] = Json::Value();
    heartbeatMessage["channel_info"]["channel_id"] = notifyChannel_->getName();
    heartbeatMessage["channel_info"]["endpoint_type"] = "framework";
    heartbeatMessage["channel_info"]["framework_id"] = frameworkId.value();
    notifyChannel_->setHeartbeatPayload(heartbeatMessage);
}

void UrbSchedulerProcess::reregistered(
      const UPID& from,
      const FrameworkID& frameworkId,
      const MasterInfo& masterInfo) {
    VLOG(1) << "UrbSchedulerProcess::reregistered(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    if (aborted_) {
      VLOG(1) << "Ignoring framework re-registered message from '" << frameworkId.value()
              << "'' because the driver is aborted!";
      return;
    }

    if (connected_) {
      VLOG(1) << "Ignoring framework re-registered message from '" << frameworkId.value()
              << "'' because the driver is already connected!";
      return;
    }

    if (master_ != from) {
      LOG(WARNING)
        << "Ignoring framework re-registered message because it was sent "
        << "from '" << from << "' instead of the leading master '"
        << master_ << "'";
      return;
    }

    LOG(INFO) << "Framework re-registered with " << frameworkId.value();

    CHECK(framework_.id().value() == frameworkId.value());

    connected_ = true;
    failover_ = false;

    startHeartbeat(frameworkId);
    pScheduler_->reregistered(pDriver_, masterInfo);

    VLOG(1) << "UrbSchedulerProcess::reregistered() end: connected="
            << connected_ << ", aborted=" << aborted_;
}

void UrbSchedulerProcess::startRegistration() {
    VLOG(1) << "UrbSchedulerProcess::startRegistration(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    registrationTimer_.delay(Seconds(0), &UrbSchedulerProcess::doReliableRegistration);
}

void UrbSchedulerProcess::doReliableRegistration() {
    LOG(INFO) << "In reliable Registration: this=" << this
              << ", connected=" << connected_ << ", aborted=" << aborted_;
    if (connected_ || master_ == "") {
      LOG(INFO) << "In reliable Registration: nothing to do";
      return;
    }
    if (aborted_) {
        VLOG(1) << "UrbSchedulerProcess::doReliableRegistration(): was aborted, already registered";
        aborted_ = false;
        connected_ = true;
        return;
    }

    try {
        getBroker()->setUrl(master_);
        createChannels();
        if ((!framework_.has_id() || framework_.id().value().empty()) || failover_) {
          VLOG(1) << "Sending registration request to " << master_ << ", failover=" << failover_;
          mesos::internal::RegisterFrameworkMessage message;
          message.mutable_framework()->MergeFrom(framework_);
          sendMessage(message);
        } else {
          // Not the first time, or failing over.
          VLOG(1) << "Sending reregistration request to " << master_ << " with framework id "
                  << framework_.id().value();
          mesos::internal::ReregisterFrameworkMessage message;
          message.mutable_framework()->MergeFrom(framework_);
          message.set_failover(failover_);
          sendMessage(message);
        }
    } catch (std::exception& e) {
        // TODO: URB... Should we send more messages to redis?
        LOG(INFO) << "Scheduling registration delay, exception: " << e.what();
        registrationTimer_.delay(Seconds(1), &UrbSchedulerProcess::doReliableRegistration);
    }
}

void UrbSchedulerProcess::resourceOffers(
      const UPID& from,
      const vector<Offer>& offers,
      const vector<string>& /*pids*/) {
    VLOG(1) << "UrbSchedulerProcess::resourceOffers(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    if (aborted_) {
      VLOG(1) << "Ignoring resource offers message because "
              << "the driver is aborted!";
      return;
    }

    if (!connected_) {
      VLOG(1) << "Ignoring resource offers message because the driver is "
              << "disconnected!";
      return;
    }

    CHECK(master_ != "");

    if (from != master_) {
      VLOG(1) << "Ignoring resource offers message because it was sent "
              << "from '" << from << "' instead of the leading master '"
              << master_ << "'";
      return;
    }

    VLOG(1) << "Received " << offers.size() << " offers";


    //TODO: URB Hook for direct messages?
    /*
    CHECK(offers.size() == pids.size());
    // Save the pid associated with each slave (one per offer) so
    // later we can send framework messages directly.
    for (size_t i = 0; i < offers.size(); i++) {
      UPID pid(pids[i]);
      // Check if parse failed (e.g., due to DNS).
      if (pid != UPID()) {
        VLOG(3) << "Saving PID '" << pids[i] << "'";
        savedOffers_[offers[i].id()][offers[i].slave_id()] = pid;
      } else {
        VLOG(1) << "Failed to parse PID '" << pids[i] << "'";
      }
    }
    */

    pScheduler_->resourceOffers(pDriver_, offers);

    VLOG(1) << "UrbSchedulerProcess::resourceOffers() end: connected="
            << connected_ << ", aborted=" << aborted_;
}

void UrbSchedulerProcess::rescindOffer(const UPID& from, const OfferID& offerId) {
    VLOG(1) << "UrbSchedulerProcess::rescindOffer(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    if (aborted_) {
      VLOG(1) << "Ignoring rescind offer message because "
              << "the driver is aborted!";
      return;
    }

    if (!connected_) {
      VLOG(1) << "Ignoring rescind offer message because the driver is "
              << "disconnected!";
      return;
    }

    CHECK(master_ != "");

    if (from != master_) {
      VLOG(1) << "Ignoring rescind offer message because it was sent "
              << "from '" << from << "' instead of the leading master '"
              << master_ << "'";
      return;
    }

    VLOG(1) << "Rescinded offer " << offerId.value();

    //TODO: This hooks up with the direct messages from above
    //savedOffers_.erase(offerId);

    pScheduler_->offerRescinded(pDriver_, offerId);

    VLOG(1) << "UrbSchedulerProcess::rescindOffer() end: connected="
            << connected_ << ", aborted=" << aborted_;
}

void UrbSchedulerProcess::statusUpdate(
      const UPID& from,
      const mesos::internal::StatusUpdate& update,
      const UPID& pid) {
    VLOG(1) << "UrbSchedulerProcess::statusUpdate(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    const TaskStatus& status = update.status();
    if (aborted_) {
      VLOG(1) << "Ignoring task status update message because "
              << "the driver is aborted!";
      return;
    }

    // Allow status updates created from the driver itself.
    if (from != UPID()) {
      if (!connected_) {
        VLOG(1) << "Ignoring status update message because the driver is "
                << "disconnected!";
        return;
      }

      CHECK(master_ != "");

      if (from != master_) {
        VLOG(1) << "Ignoring status update message because it was sent "
                << "from '" << from << "' instead of the leading master '"
                << master_ << "'";
        return;
      }
    }

    VLOG(2) << "Received status update for task " << status.task_id().value() << " on slave "
            << (status.has_slave_id() ? status.slave_id().value() : "UNKNOWN")
            << ": " << TaskState_Name(status.state());

    CHECK(framework_.id().value() == update.framework_id().value());

    pScheduler_->statusUpdate(pDriver_, status);

    // Acknowledge the status update.
    // NOTE: We do a dispatch here instead of directly sending the ACK because,
    // we want to avoid sending the ACK if the driver was aborted when we
    // made the statusUpdate call. This works because, the 'abort' message will
    // be enqueued before the ACK message is processed.
    //TODO: URB ... send an acknowledgement to ourselves...
    statusUpdateAcknowledgement(update, pid);

    // If its terminal remove from our list
    switch(status.state()) {
        case TASK_FINISHED:
        case TASK_FAILED:
        case TASK_KILLED:
        case TASK_LOST:
            if(activeTasks_.count(status.task_id().value()) > 0) {
                activeTasks_.erase(status.task_id().value());
            }
            break;
        case TASK_STAGING:
        case TASK_STARTING:
        case TASK_RUNNING:
        default:
            activeTasks_[status.task_id().value()] = status.state();
            break;
    }

    VLOG(1) << "UrbSchedulerProcess::statusUpdate() end: connected=" << connected_ << ", aborted=" << aborted_;
}

void UrbSchedulerProcess::statusUpdateAcknowledgement(const mesos::internal::StatusUpdate& update, const UPID& pid) {
    VLOG(1) << "UrbSchedulerProcess::statusUpdateAcknowledgement(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    if (aborted_) {
      VLOG(1) << "Not sending status update acknowledgment message because "
              << "the driver is aborted!";
      return;
    }

    VLOG(2) << "Sending ACK for status update "; // << update.uuid() << " to " << pid;

    mesos::internal::StatusUpdateAcknowledgementMessage message;
    message.mutable_framework_id()->MergeFrom(framework_.id());
    message.mutable_slave_id()->MergeFrom(update.has_slave_id() ? update.slave_id() : update.status().slave_id());
    message.mutable_task_id()->MergeFrom(update.status().task_id());
    message.set_uuid(update.uuid());
    sendMessage(message);
}

void UrbSchedulerProcess::lostSlave(const UPID& from, const SlaveID& slaveId) {
    VLOG(1) << "UrbSchedulerProcess::lostSlave(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    if (aborted_) {
      VLOG(1) << "Ignoring lost slave message because the driver is aborted!";
      return;
    }

    if (!connected_) {
      VLOG(1) << "Ignoring lost slave message because the driver is "
              << "disconnected!";
      return;
    }

    CHECK(master_ != "");

    if (from != master_) {
      VLOG(1) << "Ignoring lost slave message because it was sent "
              << "from '" << from << "' instead of the leading master '"
              << master_ << "'";
      return;
    }

    VLOG(1) << "Lost slave " << slaveId.value();

    savedSlavePids_.erase(slaveId.value());
    pScheduler_->slaveLost(pDriver_, slaveId);

    VLOG(1) << "UrbSchedulerProcess::lostSlave() end: connected="
            << connected_ << ", aborted=" << aborted_;
}

void UrbSchedulerProcess::frameworkMessage(const SlaveID& slaveId,
                        const FrameworkID& /*frameworkId*/,
                        const ExecutorID& executorId,
                        const string& data) {
    VLOG(1) << "UrbSchedulerProcess::frameworkMessage(): this="
            << this << ", connected=" << connected_ << ", aborted=" << aborted_;
    if (aborted_) {
      VLOG(1) << "Ignoring framework message because the driver is aborted!";
      return;
    }

    VLOG(2) << "Received framework message: connected="
            << connected_ << ", aborted=" << aborted_;

    pScheduler_->frameworkMessage(pDriver_, executorId, slaveId, data);
}

void UrbSchedulerProcess::error(const string& message) {
    VLOG(1) << "UrbSchedulerProcess::error(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    if (aborted_) {
      VLOG(1) << "Ignoring error message because the driver is aborted!";
      return;
    }

    LOG(INFO) << "Got error '" << message << "'";

    pDriver_->abort();
    pScheduler_->error(pDriver_, message);

    VLOG(1) << "UrbSchedulerProcess::error() end: connected="
            << connected_ << ", aborted=" << aborted_;
}

void UrbSchedulerProcess::stop(bool failover) {
    LOG(INFO) << "Stopping framework '" << framework_.id().value() << "', failover=" << failover
              << ", connected=" << connected_ << ", aborted=" << aborted_;

    if (connected_ && !failover) {
      mesos::internal::UnregisterFrameworkMessage message;
      message.mutable_framework_id()->MergeFrom(framework_.id());
      CHECK(master_ != "");
      sendMessage(message);
      connected_ = false; // mark as not connected anymore
//      aborted_ = true;    // TODO: mark as aborted to prevent handling messages which
                          // can arrive while evhelper thread is exiting (which can cause hanging)
                          // commented since this change breakes reregistration process
      VLOG(1) << "UrbSchedulerProcess::stop: connected=" << connected_ << ", aborted=" << aborted_;
    }

    VLOG(1) << "UrbSchedulerProcess::stop(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
}

void UrbSchedulerProcess::abort() {
    LOG(INFO) << "Aborting framework '" << framework_.id().value()
              << "', connected=" << connected_ << ", aborted=" << aborted_;

    //CHECK(aborted_);

    if (!connected_) {
      VLOG(1) << "Not sending a deactivate message as master is disconnected";
    } else {
      mesos::internal::DeactivateFrameworkMessage message;
      message.mutable_framework_id()->MergeFrom(framework_.id());
      CHECK(master_ != "");
      sendMessage(message);
      connected_ = false; // mark as not connected anymore
      aborted_ = true;
    }

    VLOG(1) << "UrbSchedulerProcess::abort(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
}

void UrbSchedulerProcess::killTask(const TaskID& taskId) {
    VLOG(1) << "UrbSchedulerProcess::killTask(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    if (!connected_) {
      VLOG(1) << "Ignoring kill task message as master is disconnected";
      return;
    }

    mesos::internal::KillTaskMessage message;
    message.mutable_framework_id()->MergeFrom(framework_.id());
    message.mutable_task_id()->MergeFrom(taskId);
    CHECK(master_ != "");
    sendMessage(message);
}

void UrbSchedulerProcess::requestResources(const vector<Request>& requests) {
    VLOG(1) << "UrbSchedulerProcess::requestResources(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    if (!connected_) {
      VLOG(1) << "Ignoring request resources message as master is disconnected";
      return;
    }

    mesos::internal::ResourceRequestMessage message;
    message.mutable_framework_id()->MergeFrom(framework_.id());
    for (const Request& request: requests) {
      message.add_requests()->MergeFrom(request);
    }
    CHECK(master_ != "");
    sendMessage(message);
}

void UrbSchedulerProcess::launchTasks(const vector<OfferID>& offerIds,
                   const vector<TaskInfo>& tasks,
                   const Filters& filters) {
    VLOG(1) << "UrbSchedulerProcess::launchTasks(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    if (!connected_) {
      VLOG(1) << "Ignoring launch tasks message as master is disconnected";
      // NOTE: Reply to the framework with TASK_LOST messages for each
      // task. This is a hack for now, to not let the scheduler
      // believe the tasks are forever in PENDING state, when actually
      // the master never received the launchTask message. Also,
      // realize that this hack doesn't capture the case when the
      // scheduler process sends it but the master never receives it
      // (message lost, master failover etc).  In the future, this
      // should be solved by the replicated log and timeouts.
      for (const TaskInfo& task: tasks) {
        mesos::internal::StatusUpdate update;
        update.mutable_framework_id()->MergeFrom(framework_.id());
        TaskStatus* status = update.mutable_status();
        status->mutable_task_id()->MergeFrom(task.task_id());
        status->set_state(TASK_LOST);
        status->set_message("Master Disconnected");
        update.set_timestamp(time(0));
        /* Generate a UUID */
        uuid_t uuid;
        uuid_generate(uuid);
        update.set_uuid((char *)uuid);

        statusUpdate(UPID(), update, UPID());
      }
      return;
    }

    vector<TaskInfo> result;

    for (const TaskInfo& task: tasks) {
      VLOG(3) << "UrbSchedulerProcess::launchTasks(): task_id=" << task.task_id().value();
      // Check that each TaskInfo has either an ExecutorInfo or a
      // CommandInfo but not both.
      if (task.has_executor() == task.has_command()) {
        mesos::internal::StatusUpdate update;
        update.mutable_framework_id()->MergeFrom(framework_.id());
        TaskStatus* status = update.mutable_status();
        status->mutable_task_id()->MergeFrom(task.task_id());
        status->set_state(TASK_LOST);
        status->set_message(
            "TaskInfo must have either an 'executor' or a 'command'");
        update.set_timestamp(time(0));
        uuid_t uuid;
        uuid_generate(uuid);
        update.set_uuid((char *)uuid);

        statusUpdate(UPID(), update, UPID());
        continue;
      }

      // Ensure the ExecutorInfo.framework_id is valid, if present.
      if (task.has_executor() &&
          task.executor().has_framework_id() &&
          !(task.executor().framework_id().value() == framework_.id().value())) {
        mesos::internal::StatusUpdate update;
        update.mutable_framework_id()->MergeFrom(framework_.id());
        TaskStatus* status = update.mutable_status();
        status->mutable_task_id()->MergeFrom(task.task_id());
        status->set_state(TASK_LOST);
        status->set_message(
            "ExecutorInfo has an invalid FrameworkID (Actual: " +
            task.executor().framework_id().value() + " vs Expected: " +
            framework_.id().value() + ")");
        update.set_timestamp(time(0));
        uuid_t uuid;
        uuid_generate(uuid);
        update.set_uuid((char *)uuid);

        statusUpdate(UPID(), update, UPID());
        continue;
      }

      TaskInfo copy = task;

      // Set the ExecutorInfo.framework_id if missing.
      if (task.has_executor() && !task.executor().has_framework_id()) {
        copy.mutable_executor()->mutable_framework_id()->CopyFrom(
            framework_.id());
      }

      // some frameworks may supply empty collection
      // remove empty collection as it is converted to incorrect json (with null value)
      if (copy.has_labels() && copy.labels().labels_size() == 0) {
        copy.clear_labels();
      }

      //Save this taskID for auto reconcile
      activeTasks_[task.task_id().value()] = TASK_STAGING;
      result.push_back(copy);
    }

    mesos::internal::LaunchTasksMessage message;
    message.mutable_framework_id()->MergeFrom(framework_.id());
    message.mutable_filters()->MergeFrom(filters);

    for (const OfferID& offerId: offerIds) {
      message.add_offer_ids()->MergeFrom(offerId);

    //TODO: URB Hook for direct messages?
    /*
      foreach (const TaskInfo& task, result) {
        // Keep only the slave PIDs where we run tasks so we can send
        // framework messages directly.
        if (savedOffers_.count(offerId.value()) > 0) {
          if (savedOffers_[offerId.value()].count(task.slave_id().value()) > 0) {
            savedSlavePids_[task.slave_id().value()] =
              savedOffers_[offerId.value()][task.slave_id().value()];
          } else {
            LOG(WARNING) << "Attempting to launch task " << task.task_id().value()
                         << " with the wrong slave id " << task.slave_id().value();
          }
        } else {
          LOG(WARNING) << "Attempting to launch task " << task.task_id().value()
                       << " with an unknown offer " << offerId.value();
        }

        // Remove the offer since we saved all the PIDs we might use.
        savedOffers_.erase(offerId.value());
      }
      */
    }

    for (const TaskInfo& task: result) {
      message.add_tasks()->MergeFrom(task);
    }

    CHECK(master_ != "");
    sendMessage(message);
}

void UrbSchedulerProcess::reviveOffers() {
    VLOG(1) << "UrbSchedulerProcess::reviveOffers(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    if (!connected_) {
      VLOG(1) << "Ignoring revive offers message as master is disconnected";
      return;
    }

    mesos::internal::ReviveOffersMessage message;
    message.mutable_framework_id()->MergeFrom(framework_.id());
    CHECK(master_ != "");
    sendMessage(message);
}

/* TODO: support suppress offers
void UrbSchedulerProcess::suppressOffers() {
    VLOG(1) << "UrbSchedulerProcess::suppressOffers()";
    if (!connected_) {
      VLOG(1) << "Ignoring revive offers message as master is disconnected";
      return;
    }

    mesos::internal::SuppressOffersMessage message;
    message.mutable_framework_id()->MergeFrom(framework_.id());
    CHECK(master_ != "");
    sendMessage(message);
}
*/

void UrbSchedulerProcess::acceptOffers(const std::vector<OfferID>& offerIds,
                      const std::vector<Offer::Operation>& operations,
                      const Filters& filters) {
    VLOG(1) << "UrbSchedulerProcess::acceptOffers(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    for (const Offer::Operation& operation: operations) {
      if (operation.type() != Offer::Operation::LAUNCH) {
        LOG(WARNING) << "acceptOffers operation " << operation.type() << " is not supported";
        continue;
      }
      vector<TaskInfo> tasks;
      for (auto& task: operation.launch().task_infos()) {
        tasks.push_back(task);
      }
      launchTasks(offerIds, tasks, filters);
    }
    VLOG(1) << "UrbSchedulerProcess::acceptOffers() end: connected="
            << connected_ << ", aborted=" << aborted_;
}

void UrbSchedulerProcess::acknowledgeStatusUpdate(const TaskStatus& status) {
    if (!connected_) {
      VLOG(1) << "Ignoring explicit status update acknowledgement"
                 " because the driver is disconnected";
      return;
    }

    CHECK(master_ != "");
    // NOTE: By ignoring the volatile 'running' here, we ensure that
    // all acknowledgements requested before the driver was stopped
    // or aborted are processed. Any acknowledgement that is requested
    // after the driver stops or aborts (running == false) will be
    // dropped in the driver before reaching here.

    // Only statuses with a 'uuid' and a 'slave_id' need to have
    // acknowledgements sent to the master. Note that the driver
    // ensures that master-generated and driver-generated updates
    // will not have a 'uuid' set.
    if (status.has_uuid() && status.has_slave_id()) {
      VLOG(2) << "Sending ACK for status update "
              << " of task " << status.task_id().value()
              << " on slave " << status.slave_id().value()
              << " to " << master_;

      mesos::internal::StatusUpdateAcknowledgementMessage message;
      message.mutable_framework_id()->CopyFrom(framework_.id());
      message.mutable_slave_id()->CopyFrom(status.slave_id());
      message.mutable_task_id()->CopyFrom(status.task_id());
      message.set_uuid(status.uuid());
      sendMessage(message);
    } else {
      VLOG(2) << "Received ACK for status update"
              << " of task " << status.task_id().value()
              << (status.has_slave_id()
                  ? " on slave " + status.slave_id().value() : "");
    }
}

void UrbSchedulerProcess::sendFrameworkMessage(const ExecutorID& executorId,
                            const SlaveID& slaveId,
                            const string& data) {
    VLOG(1) << "UrbSchedulerProcess::sendFrameworkMessage(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    if (!connected_) {
      VLOG(1) << "Ignoring send framework message as master is disconnected";
      return;
    }

    VLOG(2) << "Asked to send framework message to slave "
            << slaveId.value();

    /* TODO: URB Support direct messaging ?
    if (savedSlavePids_.count(slaveId_) > 0) {
      UPID slave = savedSlavePids_[slaveId_];
      CHECK(slave != UPID());

      FrameworkToExecutorMessage message;
      message.mutable_slave_id()->MergeFrom(slaveId_);
      message.mutable_framework_id()->MergeFrom(framework.id());
      message.mutable_executor_id()->MergeFrom(executorId_);
      message.set_data(data);
      send(slave, message);
    } else {
    */
    VLOG(2) << "Cannot send directly to slave " << slaveId.value()
              << "; sending through master";

    mesos::internal::FrameworkToExecutorMessage message;
    message.mutable_slave_id()->MergeFrom(slaveId);
    message.mutable_framework_id()->MergeFrom(framework_.id());
    message.mutable_executor_id()->MergeFrom(executorId);
    message.set_data(data);
    CHECK(master_ != "");
    sendMessage(message);
    /*}*/
    VLOG(1) << "UrbSchedulerProcess::sendFrameworkMessage() end: connected="
            << connected_ << ", aborted=" << aborted_;
}

void UrbSchedulerProcess::reconcileTasks(const vector<TaskStatus>& statuses) {
    VLOG(1) << "UrbSchedulerProcess::reconcileTasks(): this=" << this
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    if (!connected_) {
      VLOG(1) << "Ignoring task reconciliation as master is disconnected";
      return;
    }

    mesos::internal::ReconcileTasksMessage message;
    message.mutable_framework_id()->MergeFrom(framework_.id());

    LOG(INFO) << "Reconcile tasks: status count " << statuses.size();
    for (const TaskStatus& status: statuses) {
      message.add_statuses()->MergeFrom(status);
    }

    CHECK(master_ != "");
    sendMessage(message);
    VLOG(1) << "UrbSchedulerProcess::reconcileTasks() end: connected="
            << connected_ << ", aborted=" << aborted_;
}

void UrbSchedulerProcess::sendMesosMessage(google::protobuf::Message& message,
        const std::string& target, const Json::Value& extData)
{
    VLOG(2) << "UrbSchedulerProcess::sendMesosMessage() with ext data: this="
            << this << ", target=" << target
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    liburb::message_broker::Message m;
    m.setTarget(target);
    setPayload(message,m);
    m.setExtPayload(extData);
    notifyChannel_->write(m);
    VLOG(3) << "UrbSchedulerProcess::sendMesosMessage() with ext data: end";
}

void UrbSchedulerProcess::sendMesosMessage(google::protobuf::Message& message,
        const std::string& target)
{
    VLOG(2) << "UrbSchedulerProcess::sendMesosMessage(): this="
            << this << ", target=" << target
            << ", connected=" << connected_ << ", aborted=" << aborted_;
    liburb::message_broker::Message m;
    m.setTarget(target);
    setPayload(message,m);
    notifyChannel_->write(m);
    VLOG(3) << "UrbSchedulerProcess::sendMesosMessage(): end";
}

void UrbSchedulerProcess::sendMessage(mesos::internal::RegisterFrameworkMessage& m) {
    const Option<std::string> ex(os::getenv("URB_job_submit_options"));
    if (ex.isSome()) {
        Json::Value extData;
        extData["job_submit_options"] = ex.get();
        VLOG(1) << "UrbSchedulerProcess::sendMessage(): RegisterFrameworkMessage: extData=" << ex.get();
        sendMesosMessage(m, REGISTER_FRAMEWORK_TARGET, extData);
    } else {
        VLOG(1) << "UrbSchedulerProcess::sendMessage(): RegisterFrameworkMessage";
        sendMesosMessage(m, REGISTER_FRAMEWORK_TARGET);
    }
}

void UrbSchedulerProcess::sendMessage(mesos::internal::ReregisterFrameworkMessage& m) {
    VLOG(1) << "UrbSchedulerProcess::sendMessage(): ReregisterFrameworkMessage";
    sendMesosMessage(m, REREGISTER_FRAMEWORK_TARGET);
}

void UrbSchedulerProcess::sendMessage(mesos::internal::StatusUpdateAcknowledgementMessage& m) {
    VLOG(1) << "UrbSchedulerProcess::sendMessage(): StatusUpdateAcknowledgementMessage";
    sendMesosMessage(m, STATUS_UPDATE_ACKNOWLEDGEMENT_TARGET);
}

void UrbSchedulerProcess::sendMessage(mesos::internal::UnregisterFrameworkMessage& m) {
    VLOG(1) << "UrbSchedulerProcess::sendMessage(): UnregisterFrameworkMessage";
    sendMesosMessage(m, UNREGISTER_FRAMEWORK_TARGET);
}

void UrbSchedulerProcess::sendMessage(mesos::internal::DeactivateFrameworkMessage& m) {
    VLOG(1) << "UrbSchedulerProcess::sendMessage(): DeactivateFrameworkMessage";
    sendMesosMessage(m, DEACTIVATE_FRAMEWORK_TARGET);
}

void UrbSchedulerProcess::sendMessage(mesos::internal::KillTaskMessage& m) {
    VLOG(1) << "UrbSchedulerProcess::sendMessage(): KillTaskMessage";
    sendMesosMessage(m, KILL_TASK_TARGET);
}

void UrbSchedulerProcess::sendMessage(mesos::internal::ResourceRequestMessage& m) {
    VLOG(1) << "UrbSchedulerProcess::sendMessage(): ResourceRequestMessage";
    sendMesosMessage(m, RESOURCE_REQUEST_TARGET);
}

void UrbSchedulerProcess::sendMessage(mesos::internal::LaunchTasksMessage& m) {
    VLOG(1) << "UrbSchedulerProcess::sendMessage(): LaunchTasksMessage";
    sendMesosMessage(m, LAUNCH_TASKS_TARGET);
}

void UrbSchedulerProcess::sendMessage(mesos::internal::ReviveOffersMessage& m) {
    VLOG(1) << "UrbSchedulerProcess::sendMessage(): ReviveOffersMessage";
    sendMesosMessage(m, REVIVE_OFFERS_TARGET);
}

// TODO:
//void UrbSchedulerProcess::sendMessage(
//    mesos::internal::SuppressOffersMessage& m) {
//    sendMesosMessage(m, REVIVE_OFFERS_TARGET);
//}

void UrbSchedulerProcess::sendMessage(mesos::internal::FrameworkToExecutorMessage& m) {
    VLOG(1) << "UrbSchedulerProcess::sendMessage(): FrameworkToExecutorMessage";
    sendMesosMessage(m, FRAMEWORK_TO_EXECUTOR_TARGET);
}

void UrbSchedulerProcess::sendMessage(mesos::internal::ReconcileTasksMessage& m) {
    VLOG(1) << "UrbSchedulerProcess::sendMessage(): ReconcileTasksMessage";
    sendMesosMessage(m, RECONCILE_TASKS_TARGET);
}

