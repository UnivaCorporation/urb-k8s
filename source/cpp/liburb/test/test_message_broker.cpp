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

#include <gtest/gtest.h>
#include <glog/logging.h>
#include <stout/os.hpp>
#include <stout/net.hpp>

#include <json_protobuf.h>

#include <message_broker.hpp>
#include <mesos.pb.h>


using std::cerr;
using std::cout;
using std::endl;
using std::flush;
using std::string;
using std::vector;


// To use a test fixture, derive a class from testing::Test.
static bool loggingInitialized = false;
class MessageBrokerTest : public testing::Test {
protected:  // You should make the members protected s.t. they can be
    // accessed from sub-classes.

    // First time through clean up any existing log directory and set up
    // glog.
    void initializeLogging() {
        if (! loggingInitialized) {
            os::system("rm -rf /tmp/test_message_broker");
            os::system("mkdir /tmp/test_message_broker");
            FLAGS_log_dir = "/tmp/test_message_broker";
            google::InitGoogleLogging("test_message_broker");
            loggingInitialized = true;
            DLOG(INFO) << "Initializing logging.";
        }
    }

    // Make a driver instance and make sure logging is configured for our tests
    virtual void SetUp() {
        // Initialize logging
        initializeLogging();
        Try<std::string> host = net::hostname();
        url = "urb://" + host.get();

        messageBroker = liburb::message_broker::MessageBroker::getInstance();
        counter = 0;
    }

    // Truncate the log file at the end of every test and clean up any allocated driver objects.
    virtual void TearDown() {
    }
    ~MessageBrokerTest() {
        os::system("chmod -R a+w /tmp/test_message_broker");
    }

    std::shared_ptr<liburb::message_broker::MessageBroker> messageBroker;
    std::string url;
public:
    int counter;
};

// Test driver functions by calling the methods and making sure log lines
// show up.
/*
class MyCallback : public redis3m::async_callback {
  public:
    MyCallback(redis3m::async_connection::ptr_t conn, int counter);
    inline void onReply(redisAsyncContext *c, void *data) {
        redisReply *reply = static_cast<redisReply*>(data);
        if (reply == NULL) return;

        if(!disconnected && counter <= 0 && conn->is_valid() ) {
            redisAsyncDisconnect(c);
            disconnected = true;
            return;
        }
        for(int i =0; i < 2 && toschedule > 0; i++) {
            toschedule--;
            conn->execute(std::string("RPUSH mykey myvalue"),*this);
        }
        counter--;
        if (counter % 50000 == 0) {
            std::cout << "There are " << counter << " replies remaining and " << toschedule << " commands to be scheduled.\n";
        }
    }
  private:
    int counter;
    int toschedule;
    redis3m::async_connection::ptr_t conn;
    bool disconnected;
};


MyCallback::MyCallback(redis3m::async_connection::ptr_t _conn, int _counter) :
         conn(_conn), counter(_counter) {
    disconnected = false;
    toschedule = _counter;
}
*/

class MyCallback : public liburb::message_broker::Callback {
public:
    MyCallback(MessageBrokerTest *_test);
    virtual void onInput(liburb::message_broker::Channel& channel, liburb::message_broker::Message& message);

private:
    MessageBrokerTest *test;
};

class MyCallback2 : public MyCallback {
public:
    MyCallback2(MessageBrokerTest *_test) :MyCallback(_test) {};
    virtual void onInput(liburb::message_broker::Channel& channel, liburb::message_broker::Message& message);
};

MyCallback::MyCallback(MessageBrokerTest *_test) {
    test = _test;
}


void MyCallback::onInput(liburb::message_broker::Channel& /*channel*/, liburb::message_broker::Message& message) {
    test->counter++;
    std::cout << "Got My callback:" << "\n";
    std::cout << "\tcounter:\t[" << test->counter << "]\n";
    std::cout << "\tsource_id:\t[" << message.getSourceId() << "]\n";
    std::cout << "\ttarget:\t\t[" << message.getTarget() << "]\n";
    switch(message.getPayloadType()) {
    case liburb::message_broker::Message::PayloadType::JSON:
        std::cout << "\tpayload_type:\t[json]" << "\n";
        break;
    case liburb::message_broker::Message::PayloadType::PROTOBUF:
        std::cout << "\tpayload_type: [protobuf]" << "\n";
        break;
    default:
        std::cout << "\tpayload_type is INVALID!!!!" << "\n";
        break;
    }
    std::cout << "\tpayload is:\t[" << message.getPayloadAsJson().toStyledString() << "]\n";
}

void MyCallback2::onInput(liburb::message_broker::Channel& /*channel*/, liburb::message_broker::Message& message) {
    std::cout << "Got My callback2!" << message.getPayloadAsJson().toStyledString() << "\n";
}
TEST_F(MessageBrokerTest,NoMessages) {
    // /*
    try {
        std::cout << "Setting url\n";
        messageBroker->setUrl(url);
        std::string name = "broker_test_no";
        std::cout << "Creating channel" << name << "\n";
        liburb::message_broker::Channel *c = messageBroker->createChannel(name);
        std::cout << "New channel: " << c->getName() << c << "\n";
        std::shared_ptr<MyCallback> cb = std::make_shared<MyCallback>(this);
        std::cout << "Registering callback: " << &cb << "\n";
        std::cout << "Raw ptr: " << cb.get() << "\n";
        c->registerInputCallback(cb);
        std::cout << "After Register channel: " << c->getName() << c << "\n";
        sleep(1);
        std::cout << "After Register channel: " << c->getName() << c << "\n";
        sleep(1);
        std::cout << "After Register channel: " << c->getName() << c << "\n";
        sleep(1);
        std::cout << "After Register channel: " << c->getName() << c << "\n";
        sleep(1);
        std::cout << "After Register channel: " << c->getName() << c << "\n";
        sleep(1);
        cb = std::shared_ptr<MyCallback>();
        c->registerInputCallback(cb);
    }
    catch(std::exception &me)
    {
        std::cout << "StdException: " << me.what() << endl;
        ADD_FAILURE();
    }
    //delete c;
    // */
}
// Test the first constructor
TEST_F(MessageBrokerTest,Simple) {
    /*
    redis3m::reply RedisMessageBroker::rpush(std::string key, std::string value) {
       return executeCommand(redis3m::command("RPUSH") << key << value);
    }
    */
    messageBroker->setUrl(url);
    std::shared_ptr<MyCallback> cb = std::make_shared<MyCallback>(this);
    std::shared_ptr<MyCallback2> cb2 = std::make_shared<MyCallback2>(this);
    std::string name = "broker_test_another";
    std::string name2 = "broker_test_blah";
    liburb::message_broker::Channel *c = messageBroker->createChannel(name);
    // Create test driver
    mesos::ExecutorInfo executor;
    executor.mutable_executor_id()->set_value("default");
    executor.mutable_command()->set_value("127.0.0.1:5050");
    executor.set_name("Test Executor (C++)");
    executor.set_source("cpp_test");
    Json::Value framework_json;
    json_protobuf::convert_to_json(executor, framework_json);
    liburb::message_broker::Message m;
    m.setPayload(framework_json);
    std::string writeChannel = messageBroker->getEndpointName();
    writeChannel = writeChannel + ".";
    writeChannel = writeChannel + name;
    c->write(m,writeChannel);
    c->write(m,writeChannel);
    std::cout << "Test" << "\n";
    //liburb::message_broker::Channel *c2 = messageBroker->createChannel(name2);
    c->registerInputCallback(cb2);
    c->registerInputCallback(cb);
    for(int i=0; i < 10; i++) {
        c->write(m,writeChannel);
        //c2->write(m);
    }
    //messageBroker->deleteChannel(name);
    int j = 0;
    int start = time(NULL);
    while(counter < 10) {
        usleep(1000);
        j++;
        ASSERT_LT(time(NULL), start+10);
    }
    messageBroker->shutdown();
}

