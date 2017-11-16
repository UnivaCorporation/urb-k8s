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

#include <cstdint>
#include <memory>
#include <redis3m/async_connection.h>
#include <redis3m/async_connection_pool.h>
#include "timer.hpp"

namespace liburb {
namespace message_broker {

// Forward declarations
class RedisChannel;
class RedisCallback;
class RedisChannelCallback;
class RedisMessageBroker;


// BaseAsyncHandler for dealing with redis3m callbacks
class BaseAsyncHandler : public redis3m::async_callback {
public:
    BaseAsyncHandler();
    ~BaseAsyncHandler();
    BaseAsyncHandler(RedisCallback *cb);
    virtual void onReply(redisAsyncContext *c, redis3m::reply& reply);
private:
    // A pointer to the Redis callback that owns this one
    RedisCallback *callback_;
protected:
    void redisReply_json(const redis3m::reply& reply, Json::Value& json);
};

class WriteHandler : public BaseAsyncHandler {
public:
    WriteHandler();
    void onReply(redisAsyncContext *c, redis3m::reply& reply);
};

// RedisCallback for wrapping user callbacks with the necessary redis state.
class RedisCallback : public Callback {
public:
    RedisCallback(RedisChannel *channel);
    void virtual onInput(Channel& channel, Message& message) = 0;
    virtual Channel* getChannel();
private:
    // The handler that receives the redis3m message.
    std::shared_ptr<BaseAsyncHandler> asyncHandler_;
    RedisChannel *channel_;
    friend class RedisChannel;
    friend class RedisMessageBroker;
    friend class RedisChannelCallback;
};

//RedisChannelCallback The read callback for a given channel
class RedisChannelCallback : public RedisCallback {
public:
    RedisChannelCallback(RedisChannel *channel, std::shared_ptr<Callback> cb);
    virtual void onInput(Channel& channel, Message& message);
    //virtual Channel* getChannel();
private:
    //The channel that created this callback.
    friend class RedisChannel;
    //The user specified callback
    std::shared_ptr<Callback> callback_;
};

//RedisChannel class providing Message Broker channel interface
class RedisChannel : public Channel, public std::enable_shared_from_this<RedisChannel> {
public:
    RedisChannel(const std::string& name, std::shared_ptr<RedisMessageBroker> broker_);
    ~RedisChannel();
    void delete_channel();
    void registerInputCallback(std::shared_ptr<Callback> cb);
    void unregisterInputCallback(Callback *cb);
    void write(Message& message);
    void write(Message& message, const std::string& w_name);
    const std::string& getName() const;
    void setHeartbeatPayload(Json::Value& payload);
private:
    // Callback for sending periodic heartbeats
    void sendHeartbeat();
    //The helper callback
    RedisChannelCallback *callback_;
    //The broker that created this channel
    std::shared_ptr<RedisMessageBroker> broker_;
    //The name of this channel
    std::string name_;
    Timer<RedisChannel> heartbeatTimer_;
    time_t delaySeconds_;
    Message heartbeatMessage_;
    friend class RedisChannelCallback;
};

class QueuedCommand {
public:
    QueuedCommand(redis3m::command& command, std::shared_ptr<BaseAsyncHandler> ah);
    QueuedCommand();
    QueuedCommand& operator=(const QueuedCommand &rhs);
    redis3m::command command_;
    std::shared_ptr<BaseAsyncHandler> ah_;
};

//RedisMessageBroker class.  Implements the Message Broker interface.
class  RedisMessageBroker : public MessageBroker, public std::enable_shared_from_this<RedisMessageBroker> {
public:
    RedisMessageBroker();
    ~RedisMessageBroker();
    template <typename Data> bool TryPop(Data& d) { return commands_.try_pop(d); }
    Channel *createChannel(const std::string& name);
    const std::string &getEndpointName() const;
    void deleteChannel(const std::string& name);
    void setUrl(const std::string& url);
    void shutdown();
    bool getRunning() const { return isRunning_; }
    redis3m::async_connection_pool::ptr_t pool_;
    redis3m::async_connection::ptr_t conn_;
#ifndef ASYNC_WRITE
    redis3m::connection_pool::ptr_t sync_pool_;
    redis3m::connection::ptr_t sync_conn_;
#endif
private:
    // Thread for handling libev event loop processing
    void init(bool first);
    void connect();
    void sendMessage(redis3m::command& c, std::shared_ptr<BaseAsyncHandler> ah);
    volatile bool isRunning_;
    //The async connection context for this broker
    //Default async handler when we don't care about responses
    std::shared_ptr<BaseAsyncHandler> defaultHandler_;
    //Our broker unique endpoint id
//    long long endpointId_;
    int64_t endpointId_;
    std::string endpointIdStr_;
    concurrent_queue<QueuedCommand> commands_;
    int redisPort_;
    std::string redisServer_;
    std::string redisPath_;
    bool ha_;
    friend class RedisChannel;
    friend class RedisChannelCallback;
};
}
}
