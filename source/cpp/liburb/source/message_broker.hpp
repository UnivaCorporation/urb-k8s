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


#pragma once

#include <memory>

namespace liburb {
namespace message_broker {

//Forward declarations
class Callback;

// Message class that abstracts the data sent over the wire.
class Message {
public:
    // Currently we support to payload types.
    enum class PayloadType {
        JSON,
        PROTOBUF
    };

    //If this is an error, nil, or valid message
    enum class Type {
        ERROR,
        NIL,
        VALID
    };

    //Constructors
    Message();
    Message(PayloadType t);
    Message(Json::Value json);

    //Properties
    const std::string& getPayloadAsString();
    Json::Value &getPayloadAsJson();
    void setPayload(const std::string &data);
    void setPayload(Json::Value& data);
    const std::string &getTarget() const;
    Json::Value& getExtPayload();
    void setExtPayload(const Json::Value& data);
    void setTarget(const std::string& data);
    const std::string& getSourceId() const;
    void setSourceId(const std::string &data);
    PayloadType getPayloadType();
    void setPayloadType(PayloadType t);
    const std::string& getReplyTo() const;
    void setReplyTo(const std::string &data);
    Type getType() const;
    void setType(Type t);
    std::string getTypeStr() const;

    //Format for network transmission
    std::string toNetworkMessage();

private:
    //Members
    std::string payload_;
    Json::Value payloadJson_;
    Json::Value extPayload_;
    std::string target_;
    std::string sourceId_;
    std::string replyTo_;
    PayloadType payloadType_ = PayloadType::JSON;
    Type messageType_ = Type::ERROR;
};

// Pure virtual class used to model a message queue channel
class Channel {
public:
    virtual void delete_channel() = 0;
    virtual void registerInputCallback(std::shared_ptr<Callback> cb) = 0;
    virtual void unregisterInputCallback(Callback *cb) = 0;
    virtual void write(Message& message) = 0;
    virtual void write(Message& message, const std::string& w_name) = 0;
    virtual const std::string& getName() const = 0;
    virtual void setHeartbeatPayload(Json::Value& payload) = 0;
    virtual ~Channel() {};
};

// Pure virutal callback interface
class Callback {
public:
    virtual void onInput(Channel& channel, Message& message) = 0;
    virtual ~Callback() {}
};

// message broker types
enum class MessageBrokerType {
    REDIS,
};

// Singleton Message Broker interface.  Based on environmental defines
// a concrete broker is instantiated.
class  MessageBroker {
public:
    static std::shared_ptr<MessageBroker> getInstance(MessageBrokerType type = MessageBrokerType::REDIS);
    virtual Channel *createChannel(const std::string& name) = 0;
    virtual void deleteChannel(const std::string& name) = 0;
    virtual void setUrl(const std::string& url) = 0;
    virtual void shutdown() = 0;
    virtual const std::string& getEndpointName() const = 0;
    static const std::string MASTER_BROKER_MESOS_ENDPOINT;
    static const std::string HEARTBEAT_TARGET;
    static const std::string SERVICE_MONITOR_ENDPOINT;
    virtual ~MessageBroker() {}
protected:
    MessageBroker() {}
private:
};
}
}
