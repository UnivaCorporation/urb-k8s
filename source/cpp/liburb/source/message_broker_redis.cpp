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
#include <redis3m/redis3m.hpp>
#include <async.h>
#include <ev.h>
#include <thread>

#include <json/json.h>
#include <glog/logging.h>

#include "evhelper.hpp"
#include "url.hpp"
#include "concurrent_queue.hpp"
#include "message_broker.hpp"
#include "message_broker_redis.hpp"

// Some data structures to support libev multi thread notifications
typedef struct {
    ev_async async;
#if EV_MULTIPLICITY
    struct ev_loop *loop;
#endif
    std::shared_ptr<liburb::message_broker::RedisMessageBroker> pBroker;
} async_t;


async_t async_watcher;
async_t unloop_watcher;


static void async_cb(EV_P_ ev_async *w, int /*revents*/) {
    VLOG(4) << "message_broker_redis: async_cb, lock_guard in";
    // First check if we are running...  if not don't send any messages
    std::lock_guard<std::mutex> lock(liburb::EvHelper::getInstance().getMutex());
    async_t *at = static_cast<async_t*>((void*)w);
    if (!at->pBroker->getRunning()) {
        LOG(INFO) << "Ignoring notification since broker is not running";
        return;
    }
    // Don't need to do anything in here... just a notificaiton
    DLOG(INFO) << "In async";
    // Only send a message if our context is valid
    liburb::message_broker::QueuedCommand c;
    while (at->pBroker->TryPop(c)) {
        if (at->pBroker->conn_->is_valid()) {
            VLOG(4) << "async_cb: (command " << c.command_.toDebugString() << " callback: " << c.ah_;
            try {
                at->pBroker->conn_->execute(c.command_, c.ah_);
            }
            catch (std::exception& e)
            {
                LOG(ERROR) << "async_cb: (command " << c.command_.toDebugString() << " callback: " << c.ah_ << ") exception: " << e.what();
                LOG(ERROR) << "async_cb: re-throwing";
                throw;
            }
        } else {
            LOG(ERROR) << "Invalid conn in async_cb";
        }
    }
    VLOG(4) << "message_broker_redis: Done with Async Call, lock_guard out";
}

static void unloop_cb(EV_P_ ev_async *w, int /*revents*/) {
    VLOG(3) << "message_broker_redis: unloop_cb, lock_guard in";
    liburb::EvHelper& eh = liburb::EvHelper::getInstance();
    std::lock_guard<std::mutex> lock(eh.getMutex());
    async_t *at = static_cast<async_t*>((void*)w);
    at->pBroker->conn_->disconnect();
    LOG(INFO) << "Shutting down broker connection"; 
    eh.shutdown();
    VLOG(3) << "message_broker_redis: unloop_cb end, lock_guard out";
}

namespace liburb {
namespace message_broker {

// Master Broker Constants
const std::string MessageBroker::MASTER_BROKER_MESOS_ENDPOINT = "urb.endpoint.0.mesos";
const std::string MessageBroker::HEARTBEAT_TARGET = "HeartbeatMessage";
const std::string MessageBroker::SERVICE_MONITOR_ENDPOINT = "urb.service.monitor";


// RedisCallback Class
//   This class is the base concrete callback for all redis driven
//   callbacks.  Users can still base off of the Generic Callback
//   class but it will end up getting wrapped by this class.
RedisCallback::RedisCallback(RedisChannel *_channel) : channel_(_channel) {
    asyncHandler_ = std::make_shared<BaseAsyncHandler>(this);
}

Channel* RedisCallback::getChannel() {
    return channel_;
}

//BaseAsyncHandler Class
//   This class is the redis3m async callback implementing class.  It
//   gets called by redis3m when async operations complete.  It will then
//   call its RedisCallback pointer callback to bubble the event up to
//   the user callback.

// Default Contstructor... This is really only used internally for messages
// where we don't care to get any callback.
BaseAsyncHandler::BaseAsyncHandler() : callback_(nullptr) {
}

// Destructor... clean up our placeholder channel
BaseAsyncHandler::~BaseAsyncHandler() {
}

// The most common constructor.  This takes a RedisCallback that will
// get notified of redis messages.
BaseAsyncHandler::BaseAsyncHandler(RedisCallback* cb) :
    callback_(cb) {
}

// The real *meat* of this class.  This is the function that gets
// called by redis3m (through an inline static method) when a redis async
// action completes.  This method has to take the redis data and make it
// Message Broker compatible.
void BaseAsyncHandler::onReply(redisAsyncContext *c, redis3m::reply& reply) {
    VLOG(4) << "BaseAsyncHandler::onReply: reply type: " << static_cast<int>(reply.type());
    if (c == nullptr) {
        LOG(ERROR) << "BaseAsyncHandler::onReply: Got a bad reply...conext is null";
        assert(false);
        return;
    }
    if (callback_ != nullptr) {
        Message::Type messageType = Message::Type::ERROR;
        VLOG(4) << "BA Channel Name: " << callback_->getChannel()->getName();
        Json::Value parsedFromString;
        // If its an array assume that we have a BRPOP response on a single
        // with the first element being the channel name
        if (reply.type() == redis3m::reply::type_t::ARRAY &&
                reply.elements().size() == 2) {
            redisReply_json(reply.elements()[1], parsedFromString);
            messageType = Message::Type::VALID;
        } else if (reply.type() == redis3m::reply::type_t::STRING) {
            redisReply_json(reply, parsedFromString);
            messageType = Message::Type::VALID;
        } else {
            if (reply.type() == redis3m::reply::type_t::NIL) {
                messageType = Message::Type::NIL;
            }
            Message m;
            std::string mstr = m.toNetworkMessage();
            Json::Reader reader;
            reader.parse(mstr, parsedFromString);
        }

        Message message(parsedFromString);
        message.setType(messageType);
        //Call RedisCallback
        callback_->onInput(*callback_->getChannel(), message);
    } else {
        LOG(ERROR) << "BaseAsyncHandler::onReply: No redis callback...";
    }
}

// Helper function to parse redsReplies into json values
void BaseAsyncHandler::redisReply_json(const redis3m::reply& reply, Json::Value& json) {
    VLOG(2) << "BaseAsyncHandler::redisReply_json: reply=" << reply.str();
    Json::Reader reader;
    reader.parse(reply.str(), json);
}

WriteHandler::WriteHandler() : BaseAsyncHandler() {};

void WriteHandler::onReply(redisAsyncContext */*c*/, redis3m::reply& reply) {
    VLOG(4) << "WriteHandler::onReply: reply type=" << static_cast<int>(reply.type());
    if(reply.type() == redis3m::reply::type_t::INTEGER) {
        VLOG(4) << "WriteHandler::onReply: integer value is " << reply.integer();
    }
}


// RedisMessageBroker Class
// This class is the concrete implementation of the message broker.

// Default contrstructor.  This should only get called by the getInstance()
// method in the MessageBroker class.
RedisMessageBroker::RedisMessageBroker() :
    isRunning_(false),
    defaultHandler_(std::make_shared<WriteHandler>()), ha_(false) {
    ev_async_init((ev_async*)&async_watcher, async_cb);
    ev_async_init((ev_async*)&unloop_watcher, unloop_cb);
}

//Return the base name of the endpoint
const std::string& RedisMessageBroker::getEndpointName() const {
    return endpointIdStr_;
}

// The event loop.  This gets run in a separate thread so that our async
// events can be retrieved without having to run the blocking event loop in
// our main thread.
void RedisMessageBroker::init(bool first) {
    LOG(INFO) << "Initing async redis comm: first=" << first;
    if (first) {
        async_watcher.pBroker = shared_from_this();
        unloop_watcher.pBroker = shared_from_this();
        ev_async *aw = static_cast<ev_async*>((void*)&async_watcher);
        ev_async *uw = static_cast<ev_async*>((void*)&unloop_watcher);
        ev_async_start(liburb::EvHelper::getInstance().getLoop(),aw);
        ev_async_start(liburb::EvHelper::getInstance().getLoop(),uw);
    } else {
        // Build the async redis context
        if(ha_) {
            conn_ = pool_->get();
#ifndef ASYNC_WRITE
            sync_conn_ = sync_pool_->get();
#endif
        } else {
            conn_ = redis3m::async_connection::create(redisServer_, redisPort_,
                                                      liburb::EvHelper::getInstance().getLoop());
#ifndef ASYNC_WRITE
            sync_conn_ = redis3m::connection::create(redisServer_, redisPort_);
#endif
        }
    }
}

void RedisMessageBroker::connect() {
    //Create a sync connection to get our endpoint ID
    LOG(INFO) << "Attempting to connect to redis:" << redisServer_ << ":" << redisPort_;
    try {
        if (ha_) {
            pool_ = redis3m::async_connection_pool::create(redisServer_, redisPath_,
                                                           liburb::EvHelper::getInstance().getLoop(), redisPort_);
            conn_ = pool_->get();
        } else {
            conn_ = redis3m::async_connection::create(redisServer_, redisPort_,
                                                      liburb::EvHelper::getInstance().getLoop());
        }
#ifdef ASYNC_WRITE
        redis3m::connection::ptr_t c;
        if (ha) {
            c = redis3m::connection_pool::create(redisServer, redisPath, redisPort).get();
        } else {
            c = redis3m::connection::create(redisServer, redisPort);
        }
        redis3m::reply r = c->run(redis3m::command("INCR") << "urb.endpoint.id");
        c.reset();
#else
        if (ha_) {
            sync_pool_ = redis3m::connection_pool::create(redisServer_, redisPath_, redisPort_);
            sync_conn_ = sync_pool_->get();
        } else {
            sync_conn_ = redis3m::connection::create(redisServer_, redisPort_);
        }
        redis3m::reply r = sync_conn_->run(redis3m::command("INCR") << "urb.endpoint.id");
#endif
        endpointId_ = r.integer();
    } catch (std::exception& e) {
        LOG(ERROR) << "RedisMessageBroker::connect: exception: " << e.what();
        throw;
    }
    std::stringstream ss;
    ss << "urb.endpoint." << endpointId_;
    endpointIdStr_ = ss.str();
    //Start our event loop
    isRunning_ = true;
    init(true);
}

// Set the URL of the redis message broker. This can only be done once right now
void RedisMessageBroker::setUrl(const std::string &url) {
    VLOG(1) << "RedisMessageBroker::setUrl: url=" << url;
    if (isRunning_) {
        VLOG(1) << "RedisMessageBroker::setUrl: already running";
        init(false);
        return;
    }
    Try<URL> parsed_url = URL::parse(url);
    if (parsed_url.isError()) {
        //TODO: throw error
        LOG(ERROR) << "URL '" << url << "' is bad: " << parsed_url.error();
        return;
    }
    DLOG(INFO) << "URL is good";
    ha_ = parsed_url.get().ha;
    if (ha_) {
        redisServer_ = parsed_url.get().servers;
        redisPort_ = 26379;
        redisPath_ = parsed_url.get().path.substr(1);
    } else {
        // Only support single server for now
        size_t index = parsed_url.get().servers.find_last_of(':');
        if (index == std::string::npos) {
            redisPort_ = 6379;
            redisServer_ = parsed_url.get().servers;
        } else {
            redisServer_ = parsed_url.get().servers.substr(0,index);
            redisPort_ = std::stoi(parsed_url.get().servers.substr(index+1));
        }
    }
    //Trigger a connect
    connect();
}

// Create a new redis channel.  This will have to be freed by the caller.
Channel *RedisMessageBroker::createChannel(const std::string& name) {
    std::string fullName = endpointIdStr_ + ".";
    fullName += name;
    return new RedisChannel(fullName, shared_from_this());
}

// Shut down the message broker event loop and disconnect the async
// connection
void RedisMessageBroker::shutdown() {
    VLOG(1) << "RedisMessageBroker::shutdown()";
    if (isRunning_) {
        VLOG(1) << "RedisMessageBroker::shutdown(): running";
        isRunning_ = false;
        ev_async *uw = static_cast<ev_async*>((void*)&unloop_watcher);
        ev_async_send(liburb::EvHelper::getInstance().getLoop(),uw);
    }
    VLOG(1) << "RedisMessageBroker::shutdown(): done";
}

RedisMessageBroker::~RedisMessageBroker() {
    VLOG(1) << "RedisMessageBroker::~RedisMessageBroker(): lock_guard in";
    std::lock_guard<std::mutex> lock(liburb::EvHelper::getInstance().getMutex());
    // Has to be unlocked...
    shutdown();
    VLOG(1) << "RedisMessageBroker::~RedisMessageBroker(): end, lock_guard out";
}

// This method cleans up an existing message broker channel
void RedisMessageBroker::sendMessage(redis3m::command& c, std::shared_ptr<BaseAsyncHandler> ah) {
    // Only send a message if our context is valid
    //if(conn->is_valid()) conn->execute(c,ah);
    if (isRunning_ ) {
        if(!conn_) {
            LOG(INFO) << "RedisMessageBroker::sendMessage sleep 1";
            usleep(1000);
        }
    }
    if (!conn_ || !conn_->is_valid()) {
        LOG(INFO) << "RedisMessageBroker::sendMessage: Invalid connection. Not notifying. Command was " << c.toDebugString();
        return;
    }
    DLOG(INFO) << "RedisMessageBroker::sendMessage(): queuing command " << c.toDebugString();
    QueuedCommand command(c, ah);
    commands_.push(command);
    assert(ah != nullptr);
    // Notify the event loop that there is something new to listen for.
    ev_async *aw = static_cast<ev_async*>((void*)&async_watcher);
    {
        VLOG(4) << "RedisMessageBroker::sendMessage: adding callback to queue: " << ah << ", lock_guard in";
        std::lock_guard<std::mutex> lock(liburb::EvHelper::getInstance().getMutex());
        ev_async_send(liburb::EvHelper::getInstance().getLoop(), (aw));
        VLOG(4) << "RedisMessageBroker::sendMessage(): end, lock_guard out";
    }
}

// This method cleans up an existing message broker channel
void RedisMessageBroker::deleteChannel(const std::string& /*name*/) {
    VLOG(3) << "RedisMessageBroker::deleteChannel";
}

//The RedisChannelCallback class
//  This class is responsible for implementing the registerInputCallback
//  behavior of the channel.  It processes one message and then queues another
//  BRPOP to get the next one.

//Constructor taking the channel that created the callback and the user specified
// callback
RedisChannelCallback::RedisChannelCallback(RedisChannel* _channel, std::shared_ptr<Callback> _cb) :
    RedisCallback(_channel), callback_(_cb) {
}

// Handle a redis callback.  Call the user callback if set and then queue another
// pop request on this channel
void RedisChannelCallback::onInput(Channel& _channel, Message& message) {
    // We don't process callbacks if we aren't running
    if (!channel_->broker_->getRunning()) {
        LOG(INFO) << "Ignoring callback since broker is not running";
        return;
    }
    if(callback_ != nullptr) {
        //We don't notify callers of 'NIL' messages since they are likely just due to
        // BRPOP timeouts.
        if(message.getType() != Message::Type::NIL) {
            callback_->onInput(_channel, message);
        }
        //Queue the next request
        redis3m::command c = redis3m::command("BRPOP") << channel_->name_ << 1;
        channel_->broker_->sendMessage(c, asyncHandler_);
    } else {
        LOG(ERROR) << "RedisChannelCallback::onInput: Nil message Callback: " << channel_->getName();
    }
}

//The RedisChannel class.  This class is the concrete implementation of the Channel
//  interface

// Constructor taking the name of this channel as well as the broker that created it.
RedisChannel::RedisChannel(const std::string& name, std::shared_ptr<RedisMessageBroker> broker) :
  callback_(new RedisChannelCallback(this, std::shared_ptr<Callback>())),
  broker_(broker),
  name_(name),
  heartbeatTimer_(this),
  delaySeconds_(60)
{
    LOG(INFO) << "RedisChannel::RedisChannel: set name channel name to " << name;
}

// Register a new input callback for this channel and queue the first request.
// This takes affect immediately.
void RedisChannel::registerInputCallback(std::shared_ptr<Callback> cb) {
    // Reassign the user callback
    callback_->callback_ = cb;
    //Queue the next request
    if(callback_->callback_ != nullptr) {
        redis3m::command c = redis3m::command("BRPOP") << name_ << 1;
        //std::cout << "Sent message with callback: " << callback->asyncHandler << "\n";
        broker_->sendMessage(c, callback_->asyncHandler_);
    } else {
        LOG(INFO) << "RedisChannel::RedisChannel: input callback is null";
    }
}

//Send a heartbeat on this channel
void RedisChannel::sendHeartbeat() {
    try {
        LOG(INFO) << "Sending heartbeat message";
        write(heartbeatMessage_,MessageBroker::SERVICE_MONITOR_ENDPOINT);
        heartbeatTimer_.delay(Seconds(delaySeconds_),&RedisChannel::sendHeartbeat);
    } catch (std::exception& e) {
        LOG(ERROR) << "Error sending heartbeat message: exception: " << e.what();
    }
}

//Set the message we wish to use for heartbeats
void RedisChannel::setHeartbeatPayload(Json::Value& payload) {
    heartbeatMessage_.setTarget(MessageBroker::HEARTBEAT_TARGET);
    heartbeatMessage_.setPayload(payload);
    // Start heartbeat timer
    if (!heartbeatTimer_.getActive()) {
        LOG(INFO) << "Starting channel heartbeat timer";
        heartbeatTimer_.delay(Seconds(delaySeconds_),&RedisChannel::sendHeartbeat);
    }
}


//Return the name of the channel
const std::string& RedisChannel::getName() const {
    return name_;
}

// Write a message to the broker.
void RedisChannel::write(Message& message) {
    // Always set the source_id.
    // Don't write on shutdown
    if (broker_->isRunning_) {
        try {
            write(message,MessageBroker::MASTER_BROKER_MESOS_ENDPOINT);
        } catch (std::exception& e) {
            LOG(ERROR) << "RedisChannel::write: exception" << e.what();
        }
    } else {
        LOG(INFO) << "Cannot write when not running";
    }
}

// Write a message to the broker
void RedisChannel::write(Message& message, const std::string& w_name) {
    // Always set the source_id.
    message.setSourceId(broker_->endpointIdStr_);
    redis3m::command c = redis3m::command("LPUSH") << w_name <<  message.toNetworkMessage();
    try {
#ifdef ASYNC_WRITE
        VLOG(3) << "RedisChannel::write(): async";
        broker_->sendMessage(c, broker->defaultHandler);
#else
        VLOG(4) << "RedisChannel::write(): sync";
        VLOG(2) << "RedisChannel::write(): sync, message=" << message.getPayloadAsString();
        std::lock_guard<std::mutex> lock(liburb::EvHelper::getInstance().getMutex());
        broker_->sync_conn_->run(c);
        VLOG(4) << "RedisChannel::write(): sync, lock_guard out";
#endif
    } catch (std::exception& e) {
      LOG(ERROR) << "RedisChannel::write str, exception: " << e.what();
    }
}

RedisChannel::~RedisChannel() {
    delete_channel();
    LOG(INFO) << "Deleting Redis Channel";
    delete callback_;
}

// TODO
void RedisChannel::delete_channel() {
    callback_->callback_.reset();
}

// TODO
void RedisChannel::unregisterInputCallback(Callback */*cb*/) {
}

//QueueCommand Class
QueuedCommand::QueuedCommand(redis3m::command& command, std::shared_ptr<BaseAsyncHandler> ah) :
    command_(command), ah_(ah) {};

QueuedCommand::QueuedCommand() :
    command_(redis3m::command("")) {};

QueuedCommand& QueuedCommand::operator=(const QueuedCommand &rhs) {
    command_ = rhs.command_;
    ah_ = rhs.ah_;
    return *this;
}

//Namespace closures
}
}
