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


using namespace mesos;

using std::map;
using std::string;
using std::vector;

//Mesos uses this in libprocess... but we don't need such a thing
//// We do need a typedef to use the mesos function signatures though
typedef std::string UPID;

class mesos::internal::ExecutorProcess {
public:
    static const std::string REGISTER_EXECUTOR_TARGET;
    static const std::string REREGISTER_EXECUTOR_TARGET;
    static const std::string STATUS_UPDATE_TARGET;
    static const std::string EXECUTOR_TO_FRAMEWORK_TARGET;
    ExecutorProcess() {}
    virtual ~ExecutorProcess() {}
    virtual std::shared_ptr<liburb::message_broker::MessageBroker> getBroker() = 0;
    virtual void createChannels(SlaveID slaveId) = 0;
    virtual void startRegistration() = 0;
    virtual void doReliableRegistration() = 0;
    virtual void startHeartbeat() = 0;

    // The actions we can take
    virtual void registered(const ExecutorInfo& executorInfo,
                const FrameworkID& frameworkId,
                const FrameworkInfo& frameworkInfo,
                const SlaveID& slaveId,
                const SlaveInfo& slaveInfo) = 0;
    virtual void reregistered(const SlaveID& slaveId, const SlaveInfo& slaveInfo) = 0;
    virtual void reconnect(const UPID& from, const SlaveID& slaveId) = 0;
    virtual void runTask(const TaskInfo& task) = 0;
    virtual void killTask(const TaskID& taskId) = 0;
    virtual void statusUpdateAcknowledgement(
      const SlaveID& slaveId,
      const FrameworkID& frameworkId,
      const TaskID& taskId,
      const string& uuid) = 0;
    virtual void frameworkMessage(const SlaveID& slaveId,
                      const FrameworkID& frameworkId,
                      const ExecutorID& executorId,
                      const string& data) = 0;
   virtual void shutdown() = 0;

   // Additional process functions
   virtual void stop() = 0;
   virtual void abort() = 0;
   virtual void sendStatusUpdate(const TaskStatus& status) = 0;
   virtual void sendFrameworkMessage(const string& data) = 0;

    // Messages we can send
    virtual void sendMessage(
        mesos::internal::RegisterExecutorMessage& m) = 0;
    virtual void sendMessage(
        mesos::internal::StatusUpdateMessage& m) = 0;
    virtual void sendMessage(
        mesos::internal::ReregisterExecutorMessage& m) = 0;
    virtual void sendMessage(
        mesos::internal::ExecutorToFrameworkMessage& m) = 0;
};

class UrbExecutorProcess;

class ExecutorNotifyCallback : public liburb::message_broker::Callback {
public:
    ExecutorNotifyCallback(UrbExecutorProcess* process);
    virtual void onInput(liburb::message_broker::Channel& channel, liburb::message_broker::Message& message);
    enum Messages {
        EXECUTOR_REGISTERED,
        EXECUTOR_REREGISTERED,
        RECONNECT_EXECUTOR,
        RUN_TASK,
        KILL_TASK,
        STATUS_UPDATE_ACKNOWLEDGE,
        FRAMEWORK_TO_EXECUTOR,
        SHUTDOWN_EXECUTOR,
        SERVICE_DISCONNECTED
    };
private:
    UrbExecutorProcess *pProcess;
    std::map<std::string,Messages> messages;
};

class UrbExecutorProcess : public mesos::internal::ExecutorProcess {
public:
    UrbExecutorProcess(MesosExecutorDriver* pDriver,
        Executor* executor,
        const FrameworkID& frameworkId,
        const ExecutorID& executorId,
        const SlaveID& slaveId);

    ~UrbExecutorProcess();
    void setPayload(const google::protobuf::Message& gmessage,
                    liburb::message_broker::Message& message);
    virtual void createChannels(SlaveID slaveId);

    void sendMesosMessage(google::protobuf::Message& message,
                          const std::string& target);

    virtual std::shared_ptr<liburb::message_broker::MessageBroker> getBroker();
    virtual void startRegistration();
    virtual void doReliableRegistration();

    //Our actions
    virtual void registered(const ExecutorInfo& executorInfo,
                const FrameworkID& frameworkId,
                const FrameworkInfo& frameworkInfo,
                const SlaveID& slaveId,
                const SlaveInfo& slaveInfo);
    virtual void reregistered(const SlaveID& slaveId, const SlaveInfo& slaveInfo);
    virtual void reconnect(const UPID& from, const SlaveID& slaveId);
    virtual void runTask(const TaskInfo& task);
    virtual void killTask(const TaskID& taskId);
    virtual void statusUpdateAcknowledgement(
      const SlaveID& slaveId,
      const FrameworkID& frameworkId,
      const TaskID& taskId,
      const string& uuid);
    virtual void frameworkMessage(const SlaveID& slaveId,
                      const FrameworkID& frameworkId,
                      const ExecutorID& executorId,
                      const string& data);
   virtual void shutdown();

   // Additional process functions
   virtual void stop();
   virtual void abort();
   virtual void sendStatusUpdate(const TaskStatus& status);
   virtual void sendFrameworkMessage(const string& data);

    // Send our messages
    virtual void sendMessage(
        mesos::internal::RegisterExecutorMessage& m);
    virtual void sendMessage(
        mesos::internal::StatusUpdateMessage& m);
    virtual void sendMessage(
        mesos::internal::ReregisterExecutorMessage& m);
    virtual void sendMessage(
        mesos::internal::ExecutorToFrameworkMessage& m);

    virtual void startHeartbeat();
private:
    MesosExecutorDriver *pDriver_;
    Executor *pExecutor_;
    FrameworkID frameworkId_;
    ExecutorID executorId_;
    SlaveID slaveId_;
    std::shared_ptr<ExecutorNotifyCallback> notifyCallback_;
    std::shared_ptr<liburb::message_broker::MessageBroker> pBroker_;
    liburb::message_broker::Channel *notifyChannel;
    LinkedHashMap<std::string, mesos::internal::StatusUpdate> updates; // Unacknowledged tasks.
    LinkedHashMap<std::string, TaskInfo> tasks; // Unacknowledged tasks.
    liburb::Timer<UrbExecutorProcess> registrationTimer_;
    bool channelsCreated_;
    bool aborted_;
    bool connected_;
    friend class ExecutorNotifyCallback;
};

