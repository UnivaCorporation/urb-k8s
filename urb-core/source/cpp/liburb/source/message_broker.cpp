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


#include <string>
#include <json/json.h>

#include <redis3m/redis3m.hpp>
#include <thread>
#include <glog/logging.h>
#include "concurrent_queue.hpp"
#include "message_broker.hpp"
#include "message_broker_redis.hpp"


namespace liburb {
namespace message_broker {

// Singleton stuff for getting our concrete MessageBroker implementation.
std::shared_ptr<MessageBroker> MessageBroker::getInstance(MessageBrokerType type) {
    switch (type) {
    case MessageBrokerType::REDIS:
        static std::shared_ptr<MessageBroker> pInstance = std::make_shared<RedisMessageBroker>();
        return pInstance;
    default:
        assert(false);
        throw std::invalid_argument("invalid MessageBrokerType");
    }
}

// Message Class

// Default Constructor
Message::Message() {
}

// Contructor taking a 'type' of message.
Message::Message(Message::PayloadType t) : payloadType_(t) {
}

// Contructor taking a Json Value
Message::Message(Json::Value json) : messageType_(Message::Type::ERROR) {
    std::string value;
    value = json.get("target", "").asString();
    setTarget(value);
    value = json.get("source_id","").asString();
    setSourceId(value);
    value = json.get("reply_to","").asString();
    setReplyTo(value);
    if(json.isMember("ext_payload")) {
        setExtPayload(json["ext_payload"]);
    }
    setPayload(json["payload"]);
    setPayloadType(Message::PayloadType::JSON);
}

// Properties
void Message::setPayload(const std::string& data) {
    if(payloadType_ == Message::PayloadType::JSON) {
        // Neet to convert this to json...
        Json::Reader reader;
        reader.parse(data,payloadJson_);
    }
    payload_ = data;
}

void Message::setPayload(Json::Value& data) {
    //Json::FastWriter fastWriter;
    //payload = fastWriter.write(data);
    payloadJson_ = data;
}

const std::string &Message::getPayloadAsString() {
    if(payloadType_ == Message::PayloadType::JSON) {
        // Need to convert our JSON to a string
        Json::FastWriter fastWriter;
        payload_ = fastWriter.write(payloadJson_);
    }
    return payload_;
}

Json::Value& Message::getPayloadAsJson() {
    return payloadJson_;
}

void Message::setExtPayload(const Json::Value& data) {
    extPayload_ = data;
}

Json::Value& Message::getExtPayload() {
    return extPayload_;
}

void Message::setType(Type t){
    messageType_ = t;
}

Message::Type Message::getType() const {
    return messageType_;
}
std::string Message::getTypeStr() const {
    switch (messageType_) {
    case Type::ERROR:
        return "ERROR";
    case Type::VALID:
        return "VALID";
    case Type::NIL:
        return "NIL";
    default:
        return std::to_string(static_cast<int>(messageType_));
    }
}

void Message::setSourceId(const std::string& data) {
    sourceId_ = data;
}

const std::string &Message::getSourceId() const {
    return sourceId_;
}

void Message::setReplyTo(const std::string& data) {
    replyTo_ = data;
}

const std::string &Message::getReplyTo() const {
    return replyTo_;
}

void Message::setTarget(const std::string& data) {
    target_ = data;
}

const std::string& Message::getTarget() const {
    return target_;
}

void Message::setPayloadType(Message::PayloadType t) {
    if (t != payloadType_) {
        switch(payloadType_) {
        case Message::PayloadType::JSON:
            //Nothing to do here...
            break;
        case Message::PayloadType::PROTOBUF:
            payload_.clear();
            break;
        default:
            break;
        }
    }
}

Message::PayloadType Message::getPayloadType() {
    return payloadType_;
}


// Format this message for transport over the wire.
std::string Message::toNetworkMessage() {
    Json::Value root;
    root["target"] = getTarget();
    root["source_id"] = getSourceId();
    root["ext_payload"] = getExtPayload();
    switch (getPayloadType()) {
    case Message::PayloadType::JSON:
        root["payload"] = getPayloadAsJson();
        root["payload_type"] = "json";
        break;
    case Message::PayloadType::PROTOBUF:
        root["payload_type"] = "protobuf";
        root["payload"] = getPayloadAsString();
        break;
    default:
        LOG(FATAL) << "Unexpected payload type";
        break;
    }
    if(getReplyTo() != "") {
        root["reply_to"] = getReplyTo();
    }
    Json::FastWriter fastWriter;
    return fastWriter.write(root);
}

}
}
