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
#include <fstream>

#include <json_protobuf.h>
#include <message_broker.hpp>
#include <mesos/executor.hpp>
#include <mesos.pb.h>
#include <messages.pb.h>
#include <stout/linkedhashmap.hpp>
#include <stout/os.hpp>
#include <json_protobuf.h>

#include "timer.hpp"
#include <executor_process.hpp>

#include <gtest/gtest.h>
#include <glog/logging.h>
#include <redis3m/redis3m.hpp>

using namespace mesos;

// To use a test fixture, derive a class from testing::Test.
static bool loggingInitialized = false;
static UrbExecutorProcess* pProcess = NULL;
static FrameworkID frameworkId;
static ExecutorID executorId;
static SlaveID slaveId;
class ExecutorMessagesTest : public testing::Test {
protected:  // You should make the members protected s.t. they can be
    // accessed from sub-classes.

    // First time through clean up any existing log directory and set up
    // glog.
    void initializeLogging() {
        if (! loggingInitialized) {
            os::system("rm -rf /tmp/test_exec_messages");
            os::system("mkdir /tmp/test_exec_messages");
            FLAGS_log_dir = "/tmp/test_exec_messages";
            google::InitGoogleLogging("test_exec_messages");
            loggingInitialized = true;
            DLOG(INFO) << "Initializing logging.";
        }
    }

    // Make a driver instance and make sure logging is configured for our tests
    virtual void SetUp() {
        // Initialize logging
        initializeLogging();

        std::string url = "urb://localhost:6379";
        conn = redis3m::connection::create("localhost",6379);
        //redis3m::reply r = c->run(redis3m::command("INCR") << "urb.endpoint.id");
        if(pProcess == NULL) {
            slaveId.set_value("1234");
            pProcess = new UrbExecutorProcess(NULL,NULL, frameworkId, executorId, slaveId/*, NULL, NULL*/);
            pProcess->getBroker()->setUrl(url);
            pProcess->createChannels(slaveId);
        }
    }

    // Truncate the log file at the end of every test and clean up any allocated driver objects.
    virtual void TearDown() {
    }

    ~ExecutorMessagesTest() {
        os::system("chmod -R a+w /tmp/test_exec_messages");
    }

    redis3m::connection::ptr_t    conn;
};
// Test the first constructor
TEST_F(ExecutorMessagesTest,DefaultConstructor) {
    ASSERT_NE((UrbExecutorProcess*)NULL, pProcess);
}
TEST_F(ExecutorMessagesTest,RegisterExecutor) {
    mesos::internal::RegisterExecutorMessage m;
    pProcess->sendMessage(m);
    redis3m::reply r = conn->run(redis3m::command("BLPOP") << "urb.endpoint.0.mesos" << "5" );
    ASSERT_EQ(r.type(), redis3m::reply::type_t::ARRAY);
    ASSERT_EQ(r.elements()[1].type(),redis3m::reply::type_t::STRING);
    DLOG(INFO) << "RegisterExecutor" << r.elements()[1].str();
    Json::Value json;
    Json::Reader reader;
    reader.parse(r.elements()[1].str(),json);
    liburb::message_broker::Message message(json);
    mesos::internal::RegisterExecutorMessage m2;
    ASSERT_EQ(message.getPayloadAsJson().isMember("mesos.internal.RegisterExecutorMessage"), true);
    //json_protobuf::update_from_json(message.getPayloadAsJson(),m2);
}
TEST_F(ExecutorMessagesTest,ReregisterExecutor) {
    mesos::internal::ReregisterExecutorMessage m;
    pProcess->sendMessage(m);
    redis3m::reply r = conn->run(redis3m::command("BLPOP") << "urb.endpoint.0.mesos" << "5" );
    ASSERT_EQ(r.type(), redis3m::reply::type_t::ARRAY);
    ASSERT_EQ(r.elements()[1].type(),redis3m::reply::type_t::STRING);
    DLOG(INFO) << "Reregister" << r.elements()[1].str();
    Json::Value json;
    Json::Reader reader;
    reader.parse(r.elements()[1].str(),json);
    liburb::message_broker::Message message(json);
    mesos::internal::ReregisterExecutorMessage m2;
    ASSERT_EQ(message.getPayloadAsJson().isMember("mesos.internal.ReregisterExecutorMessage"), true);
    /*
    json_protobuf::update_from_json(message.getPayloadAsJson(),m2);
    */
}
TEST_F(ExecutorMessagesTest,StatusUpdateMessage) {
    mesos::internal::StatusUpdateMessage m;
    pProcess->sendMessage(m);
    redis3m::reply r = conn->run(redis3m::command("BLPOP") << "urb.endpoint.0.mesos" << "5" );
    ASSERT_EQ(r.type(), redis3m::reply::type_t::ARRAY);
    ASSERT_EQ(r.elements()[1].type(),redis3m::reply::type_t::STRING);
    DLOG(INFO) << "StatusUpdate" << r.elements()[1].str();
    Json::Value json;
    Json::Reader reader;
    reader.parse(r.elements()[1].str(),json);
    liburb::message_broker::Message message(json);
    mesos::internal::StatusUpdateMessage m2;
    ASSERT_EQ(message.getPayloadAsJson().isMember("mesos.internal.StatusUpdateMessage"), true);
    /*
    json_protobuf::update_from_json(message.getPayloadAsJson(),m2);
    */
}
TEST_F(ExecutorMessagesTest,ExecutorToFramework) {
    mesos::internal::ExecutorToFrameworkMessage m;
    pProcess->sendMessage(m);
    redis3m::reply r = conn->run(redis3m::command("BLPOP") << "urb.endpoint.0.mesos" << "5" );
    ASSERT_EQ(r.type(), redis3m::reply::type_t::ARRAY);
    ASSERT_EQ(r.elements()[1].type(),redis3m::reply::type_t::STRING);
    DLOG(INFO) << "ExecutorToFramework" << r.elements()[1].str();
    Json::Value json;
    Json::Reader reader;
    reader.parse(r.elements()[1].str(),json);
    liburb::message_broker::Message message(json);
    mesos::internal::ExecutorToFrameworkMessage m2;
    ASSERT_EQ(message.getPayloadAsJson().isMember("mesos.internal.ExecutorToFrameworkMessage"), true);
    /*
    json_protobuf::update_from_json(message.getPayloadAsJson(),m2);
    */
}
