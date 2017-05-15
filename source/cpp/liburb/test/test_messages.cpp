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
#include <mesos/scheduler.hpp>
#include <mesos.pb.h>
#include <messages.pb.h>
#include <authentication.pb.h>
#include "timer.hpp"
#include <scheduler_process.hpp>

#include <gtest/gtest.h>
#include <glog/logging.h>
#include <redis3m/redis3m.hpp>
#include <stout/os.hpp>

using namespace mesos;

// To use a test fixture, derive a class from testing::Test.
static bool loggingInitialized = false;
static UrbSchedulerProcess* pProcess = NULL;
static FrameworkInfo framework;
class MessagesTest : public testing::Test {
protected:  // You should make the members protected s.t. they can be
    // accessed from sub-classes.

    // First time through clean up any existing log directory and set up
    // glog.
    void initializeLogging() {
        if (! loggingInitialized) {
            os::system("rm -rf /tmp/test_messages");
            os::system("mkdir /tmp/test_messages");
            FLAGS_log_dir = "/tmp/test_messages";
            google::InitGoogleLogging("test_messages");
            loggingInitialized = true;
            DLOG(INFO) << "Initializing logging.";
        }
    }

    // Make a driver instance and make sure logging is configured for our tests
    virtual void SetUp() {
        // Initialize logging
        initializeLogging();

        std::string url = "urb://localhost:6379";
        conn = redis3m::connection::create("localhost", 6379);
        //redis3m::reply r = c->run(redis3m::command("INCR") << "urb.endpoint.id");
        if(pProcess == NULL) {
            pProcess = new UrbSchedulerProcess(NULL,NULL, framework, url/*, NULL, NULL*/);
            pProcess->getBroker()->setUrl(url);
            pProcess->createChannels();
        }
    }

    // Truncate the log file at the end of every test and clean up any allocated driver objects.
    virtual void TearDown() {
    }

    ~MessagesTest() {
        os::system("chmod -R a+w /tmp/test_messages");
    }

    redis3m::connection::ptr_t    conn;
};

// Test driver functions by calling the methods and making sure log lines
// show up.

// Test the first constructor
TEST_F(MessagesTest,DefaultConstructor) {
    ASSERT_NE((UrbSchedulerProcess*)NULL, pProcess);
}
TEST_F(MessagesTest,RegisterFramework) {
    mesos::internal::RegisterFrameworkMessage m;
    pProcess->sendMessage(m);
    redis3m::reply r = conn->run(redis3m::command("BLPOP") << "urb.endpoint.0.mesos" << "5" );
    ASSERT_EQ(r.type(), redis3m::reply::type_t::ARRAY);
    ASSERT_EQ(r.elements()[1].type(),redis3m::reply::type_t::STRING);
    //std::cout << r.elements()[1].str() << "\n";
    DLOG(INFO) << "RegisterFramework" << r.elements()[1].str();
}
TEST_F(MessagesTest,STATUS_UPDATE_ACKNOWLEDGEMENT_TARGET) {
    mesos::internal::StatusUpdateAcknowledgementMessage m;
    pProcess->sendMessage(m);
    redis3m::reply r = conn->run(redis3m::command("BLPOP") << "urb.endpoint.0.mesos" << "5" );
    ASSERT_EQ(r.type(), redis3m::reply::type_t::ARRAY);
    ASSERT_EQ(r.elements()[1].type(),redis3m::reply::type_t::STRING);
    //std::cout << r.elements()[1].str() << "\n";
    DLOG(INFO) << "StatusUpdate" << r.elements()[1].str();
}
TEST_F(MessagesTest,UNREGISTER_FRAMEWORK_TARGET) {
    mesos::internal::UnregisterFrameworkMessage m;
    pProcess->sendMessage(m);
    redis3m::reply r = conn->run(redis3m::command("BLPOP") << "urb.endpoint.0.mesos" << "5" );
    ASSERT_EQ(r.type(), redis3m::reply::type_t::ARRAY);
    ASSERT_EQ(r.elements()[1].type(),redis3m::reply::type_t::STRING);
    //std::cout << r.elements()[1].str() << "\n";
    DLOG(INFO) << "UnregisterFramework" << r.elements()[1].str();
}
TEST_F(MessagesTest,DEACTIVATE_FRAMEWORK_TARGET) {
    mesos::internal::DeactivateFrameworkMessage m;
    pProcess->sendMessage(m);
    redis3m::reply r = conn->run(redis3m::command("BLPOP") << "urb.endpoint.0.mesos" << "5" );
    ASSERT_EQ(r.type(), redis3m::reply::type_t::ARRAY);
    ASSERT_EQ(r.elements()[1].type(),redis3m::reply::type_t::STRING);
    //std::cout << r.elements()[1].str() << "\n";
    DLOG(INFO) << "Deactivate" << r.elements()[1].str();
}
TEST_F(MessagesTest,KILL_TASK_TARGET) {
    mesos::internal::KillTaskMessage m;
    pProcess->sendMessage(m);
    redis3m::reply r = conn->run(redis3m::command("BLPOP") << "urb.endpoint.0.mesos" << "5" );
    ASSERT_EQ(r.type(), redis3m::reply::type_t::ARRAY);
    ASSERT_EQ(r.elements()[1].type(),redis3m::reply::type_t::STRING);
    //std::cout << r.elements()[1].str() << "\n";
    DLOG(INFO) << "KillTask" << r.elements()[1].str();
}
TEST_F(MessagesTest,RESOURCE_REQUEST_TARGET) {
    mesos::internal::ResourceRequestMessage m;
    pProcess->sendMessage(m);
    redis3m::reply r = conn->run(redis3m::command("BLPOP") << "urb.endpoint.0.mesos" << "5" );
    ASSERT_EQ(r.type(), redis3m::reply::type_t::ARRAY);
    ASSERT_EQ(r.elements()[1].type(),redis3m::reply::type_t::STRING);
    //std::cout << r.elements()[1].str() << "\n";
    DLOG(INFO) << "ResourceRequest" << r.elements()[1].str();
}
TEST_F(MessagesTest,LAUNCH_TASKS_TARGET) {
    mesos::internal::LaunchTasksMessage m;
    pProcess->sendMessage(m);
    redis3m::reply r = conn->run(redis3m::command("BLPOP") << "urb.endpoint.0.mesos" << "5" );
    ASSERT_EQ(r.type(), redis3m::reply::type_t::ARRAY);
    ASSERT_EQ(r.elements()[1].type(),redis3m::reply::type_t::STRING);
    //std::cout << r.elements()[1].str() << "\n";
    DLOG(INFO) <<"LaunchTasks" << r.elements()[1].str();
}
TEST_F(MessagesTest,REVIVE_OFFERS_TARGET) {
    mesos::internal::ReviveOffersMessage m;
    pProcess->sendMessage(m);
    redis3m::reply r = conn->run(redis3m::command("BLPOP") << "urb.endpoint.0.mesos" << "5" );
    ASSERT_EQ(r.type(), redis3m::reply::type_t::ARRAY);
    ASSERT_EQ(r.elements()[1].type(),redis3m::reply::type_t::STRING);
    //std::cout << r.elements()[1].str() << "\n";
    DLOG(INFO) << "ReviveOffers" << r.elements()[1].str();
}
TEST_F(MessagesTest,FRAMEWORK_TO_EXECUTOR_TARGET) {
    mesos::internal::FrameworkToExecutorMessage m;
    pProcess->sendMessage(m);
    redis3m::reply r = conn->run(redis3m::command("BLPOP") << "urb.endpoint.0.mesos" << "5" );
    ASSERT_EQ(r.type(), redis3m::reply::type_t::ARRAY);
    ASSERT_EQ(r.elements()[1].type(),redis3m::reply::type_t::STRING);
    //std::cout << r.elements()[1].str() << "\n";
    DLOG(INFO) << "FrameworkToExecutor" << r.elements()[1].str();
}
TEST_F(MessagesTest,RECONCILE_TASKS_TARGET) {
    mesos::internal::ReconcileTasksMessage m;
    pProcess->sendMessage(m);
    redis3m::reply r = conn->run(redis3m::command("BLPOP") << "urb.endpoint.0.mesos" << "5" );
    ASSERT_EQ(r.type(), redis3m::reply::type_t::ARRAY);
    ASSERT_EQ(r.elements()[1].type(),redis3m::reply::type_t::STRING);
    DLOG(INFO) << "ReconcileTasks" << r.elements()[1].str();
}

TEST_F(MessagesTest,JSON_BINARY1) {
    mesos::internal::AuthenticationStepMessage m;
    std::string data("12\00034",5);
    m.set_data(data);
    Json::Value j;
    //std::cout << "Message Debug String: " << m.DebugString() << "\n";
    json_protobuf::convert_to_json(m,j);
    ASSERT_EQ(j["data"],"MTIAMzQ=\n");
    //std::cout << "JSON Data: " << j.toStyledString() << "\n";
    json_protobuf::update_from_json(j,m);
    //std::cout << "Message Debug String2: " << m.DebugString() << "\n";
    ASSERT_EQ(data,m.data());
    std::stringstream ss;
    for(int i=0; i < 512; i++) {
        ss << (char)(i%256);
    }
    m.set_data(ss.str());
    std::cout << "Message Debug String: " << m.DebugString() << "\n";
    json_protobuf::convert_to_json(m,j);
    //ASSERT_EQ(j["data"],"MTIAMzQ=\n");
    std::cout << "JSON Data: " << j.toStyledString() << "\n";
    json_protobuf::update_from_json(j,m);
    std::cout << "Message Debug String2: " << m.DebugString() << "\n";
    ASSERT_EQ(ss.str(),m.data());
}
