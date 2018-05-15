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


#include <memory>

using namespace mesos;

using std::map;
using std::string;
using std::vector;


class UrbSchedulerProcess;

// Mesos uses this in libprocess... but we don't need such a thing
// We do need a typedef to use the mesos function signatures though
typedef std::string UPID;

class mesos::internal::SchedulerProcess {
public:
    static const std::string REGISTER_FRAMEWORK_TARGET;
    static const std::string REREGISTER_FRAMEWORK_TARGET;
    static const std::string STATUS_UPDATE_ACKNOWLEDGEMENT_TARGET;
    static const std::string UNREGISTER_FRAMEWORK_TARGET;
    static const std::string DEACTIVATE_FRAMEWORK_TARGET;
    static const std::string KILL_TASK_TARGET;
    static const std::string RESOURCE_REQUEST_TARGET;
    static const std::string LAUNCH_TASKS_TARGET;
    static const std::string REVIVE_OFFERS_TARGET;
    static const std::string SUPPRESS_OFFERS_TARGET;
    static const std::string FRAMEWORK_TO_EXECUTOR_TARGET;
    static const std::string RECONCILE_TASKS_TARGET;
    SchedulerProcess() {};
    virtual ~SchedulerProcess() {};
    virtual std::shared_ptr<liburb::message_broker::MessageBroker> getBroker() = 0;
    virtual void createChannels() = 0;
    virtual void checkReconcile() = 0;
    virtual void startHeartbeat(const FrameworkID& frameworkId) = 0;

    // Actions we can take
    // TODO: authentication
    //virtual void authenticate() = 0;
    //virtual void _authenticate() = 0;
    //void authenticationTimeout(Future<bool> future) = 0;
    virtual void registered(
      const UPID& from,
      const FrameworkID& frameworkId,
      const MasterInfo& masterInfo) = 0;
    virtual void reregistered(
      const UPID& from,
      const FrameworkID& frameworkId,
      const MasterInfo& masterInfo) = 0;
    virtual void startRegistration() = 0;
    virtual void doReliableRegistration() = 0;
    virtual void resourceOffers(
      const UPID& from,
      const vector<Offer>& offers,
      const vector<string>& pids) = 0;
    virtual void rescindOffer(const UPID& from, const OfferID& offerId) = 0;
    virtual void statusUpdate(
      const UPID& from,
      const StatusUpdate& update,
      const UPID& pid) = 0;
    virtual void statusUpdateAcknowledgement(const StatusUpdate& update, const UPID& pid) = 0;
    virtual void lostSlave(const UPID& from, const SlaveID& slaveId) = 0;
    virtual void frameworkMessage(const SlaveID& slaveId,
                        const FrameworkID& frameworkId,
                        const ExecutorID& executorId,
                        const string& data) = 0;
    virtual void error(const string& message) = 0;
    virtual void stop(bool failover) = 0;
    virtual void abort() = 0;
    virtual void killTask(const TaskID& taskId) = 0;
    virtual void requestResources(const vector<Request>& requests) = 0;
    virtual void launchTasks(const vector<OfferID>& offerIds,
                   const vector<TaskInfo>& tasks,
                   const Filters& filters) = 0;
    virtual void reviveOffers() = 0;
    virtual void sendFrameworkMessage(const ExecutorID& executorId,
                            const SlaveID& slaveId,
                            const string& data) = 0;
    virtual void reconcileTasks(const vector<TaskStatus>& statuses) = 0;
    virtual void acceptOffers(const std::vector<OfferID>& offerIds,
                   const std::vector<Offer::Operation>& operations,
                   const Filters& filters) = 0;
    virtual void acknowledgeStatusUpdate(const TaskStatus& st) = 0;
    // The messages we can send
    virtual void sendMessage(
        mesos::internal::RegisterFrameworkMessage& rfm) = 0;
    virtual void sendMessage(
        mesos::internal::ReregisterFrameworkMessage& m) = 0;
    virtual void sendMessage(
        mesos::internal::StatusUpdateAcknowledgementMessage& m) = 0;
    virtual void sendMessage(
        mesos::internal::UnregisterFrameworkMessage& m) = 0;
    virtual void sendMessage(
        mesos::internal::DeactivateFrameworkMessage& m) = 0;
    virtual void sendMessage(
        mesos::internal::KillTaskMessage& m) = 0;
    virtual void sendMessage(
        mesos::internal::ResourceRequestMessage& m) = 0;
    virtual void sendMessage(
        mesos::internal::LaunchTasksMessage& m) = 0;
    virtual void sendMessage(
        mesos::internal::ReviveOffersMessage& m) = 0;
//TODO:    virtual void sendMessage(
//        mesos::internal::SuppressOffersMessage& m) = 0;
    virtual void sendMessage(
        mesos::internal::FrameworkToExecutorMessage& m) = 0;
    virtual void sendMessage(
        mesos::internal::ReconcileTasksMessage& m) = 0;
};

class SchedulerNotifyCallback : public liburb::message_broker::Callback {
public:
    SchedulerNotifyCallback(UrbSchedulerProcess* process);
    enum Messages {
        FRAMEWORK_REGISTERED,
        FRAMEWORK_REREGISTERED,
        RESOURCE_OFFERS,
        RESCIND_RESOURCE_OFFER,
        STATUS_UPDATE,
        LOST_SLAVE,
        EXECUTOR_TO_FRAMEWORK,
        FRAMEWORK_ERROR,
        SERVICE_DISCONNECTED
    };
    virtual void onInput(liburb::message_broker::Channel& channel, liburb::message_broker::Message& message);
private:
    UrbSchedulerProcess *pProcess_;
    std::map<std::string, Messages> messages_ {
            {"FrameworkRegisteredMessage", FRAMEWORK_REGISTERED},
            {"FrameworkReregisteredMessage", FRAMEWORK_REREGISTERED},
            {"ResourceOffersMessage", RESOURCE_OFFERS},
            {"ExecutorToFrameworkMessage", EXECUTOR_TO_FRAMEWORK},
            {"StatusUpdateMessage", STATUS_UPDATE},
            {"RescindResourceOfferMessage", RESCIND_RESOURCE_OFFER},
            {"LostSlaveMessage", LOST_SLAVE},
            {"FrameworkErrorMessage", FRAMEWORK_ERROR},
            {"ServiceDisconnectedMessage", SERVICE_DISCONNECTED}
    };
};

class UrbSchedulerProcess : public mesos::internal::SchedulerProcess {
public:
    UrbSchedulerProcess(MesosSchedulerDriver* pDriver,
                        Scheduler* scheduler,
                        const FrameworkInfo& framework,
                        std::string master);
    ~UrbSchedulerProcess();
    void setPayload(const google::protobuf::Message& gmessage,
                    liburb::message_broker::Message& message);
    virtual void createChannels();
    virtual void checkReconcile();
    void sendMesosMessage(google::protobuf::Message& message,
                          const std::string& target);
    void sendMesosMessage(google::protobuf::Message& message,
                          const std::string& target, const Json::Value& extData);
    virtual std::shared_ptr<liburb::message_broker::MessageBroker> getBroker();

    // Actions we can take
    // TODO: authentication
    //void authenticate();
    //void _authenticate();
    //void authenticationTimeout(Future<bool> future);
     void registered(
      const UPID& from,
      const FrameworkID& frameworkId,
      const MasterInfo& masterInfo);
    void reregistered(
      const UPID& from,
      const FrameworkID& frameworkId,
      const MasterInfo& masterInfo);
    void startRegistration();
    void doReliableRegistration();
    void resourceOffers(
      const UPID& from,
      const vector<Offer>& offers,
      const vector<string>& pids);
    void rescindOffer(const UPID& from, const OfferID& offerId);
    void statusUpdate(
      const UPID& from,
      const mesos::internal::StatusUpdate& update,
      const UPID& pid);
    void statusUpdateAcknowledgement(const mesos::internal::StatusUpdate& update, const UPID& pid);
    void lostSlave(const UPID& from, const SlaveID& slaveId);
    void frameworkMessage(const SlaveID& slaveId,
                        const FrameworkID& frameworkId,
                        const ExecutorID& executorId,
                        const string& data);
    void error(const string& message);
    void stop(bool failover);
    void abort();
    void killTask(const TaskID& taskId);
    void requestResources(const vector<Request>& requests);
    void launchTasks(const vector<OfferID>& offerIds,
                   const vector<TaskInfo>& tasks,
                   const Filters& filters);
    void reviveOffers();
    void sendFrameworkMessage(const ExecutorID& executorId,
                            const SlaveID& slaveId,
                            const string& data);
    void reconcileTasks(const vector<TaskStatus>& statuses);
    void acceptOffers(const std::vector<OfferID>& offerIds,
                      const std::vector<Offer::Operation>& operations,
                      const Filters& filters);
    void acknowledgeStatusUpdate(const TaskStatus& st);
    //Messages we can send
    virtual void sendMessage(mesos::internal::RegisterFrameworkMessage& rfm);
    virtual void sendMessage(
        mesos::internal::ReregisterFrameworkMessage& m);
    virtual void sendMessage(
        mesos::internal::StatusUpdateAcknowledgementMessage& m);
    virtual void sendMessage(
        mesos::internal::UnregisterFrameworkMessage& m);
    virtual void sendMessage(
        mesos::internal::DeactivateFrameworkMessage& m);
    virtual void sendMessage(
        mesos::internal::KillTaskMessage& m);
    virtual void sendMessage(
        mesos::internal::ResourceRequestMessage& m);
    virtual void sendMessage(
        mesos::internal::LaunchTasksMessage& m);
    virtual void sendMessage(
        mesos::internal::ReviveOffersMessage& m);
//TODO:    virtual void sendMessage(
//        mesos::internal::SuppressOffersMessage& m);
    virtual void sendMessage(
        mesos::internal::FrameworkToExecutorMessage& m);
    virtual void sendMessage(
        mesos::internal::ReconcileTasksMessage& m);
    virtual void startHeartbeat(const FrameworkID& frameworkId);
private:
    std::shared_ptr<liburb::message_broker::MessageBroker> pBroker_;
    bool channelsCreated_;
    std::shared_ptr<SchedulerNotifyCallback> notifyCallback_;
    liburb::message_broker::Channel *pNotifyChannel_;

    MesosSchedulerDriver *pDriver_;
    Scheduler *pScheduler_;
    FrameworkInfo framework_;
    bool failover_;
    std::string master_;
    bool connected_; // Flag to indicate if framework is registered.
    volatile bool aborted_; // Flag to indicate if the driver is running.

    std::map<std::string, std::map<std::string, UPID> > savedOffers_;
    std::map<std::string, UPID> savedSlavePids_;
    std::map<std::string, TaskState> activeTasks_;

    //TODO:
    //const Option<Credential> credential;
    //TODO:
    //Authenticatee* authenticatee;
    //TODO:
    // Indicates if an authentication attempt is in progress.
    //Option<Future<bool> > authenticating;

    // Indicates if the authentication is successful.
    bool authenticated_;

    // Indicates if a new authentication attempt should be enforced.
    bool reauthenticate_;

    liburb::Timer<UrbSchedulerProcess> registrationTimer_;
    liburb::Timer<UrbSchedulerProcess> reconcileTimer_;

    friend class SchedulerNotifyCallback;
};
