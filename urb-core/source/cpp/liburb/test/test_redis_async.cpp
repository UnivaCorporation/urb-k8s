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

#include <redis3m/redis3m.hpp>
#include <redis3m/async_connection.h>
#include <async.h>
#include <ev.h>
#include "evhelper.hpp"

#include <gtest/gtest.h>
#include <glog/logging.h>
#include <stout/os.hpp>

using std::cerr;
using std::cout;
using std::endl;
using std::flush;
using std::string;
using std::vector;


// To use a test fixture, derive a class from testing::Test.
static bool loggingInitialized = false;
class RedisAsyncTest : public testing::Test {
protected:  // You should make the members protected s.t. they can be
    // accessed from sub-classes.

    // First time through clean up any existing log directory and set up
    // glog.
    void initializeLogging() {
        if (!loggingInitialized) {
            os::system("rm -rf /tmp/test_redis");
            os::system("mkdir /tmp/test_redis");
            FLAGS_log_dir = "/tmp/test_redis";
            google::InitGoogleLogging("test_redis");
            loggingInitialized = true;
            LOG(INFO) << "Initializing logging.";
        }
    }

    // Make a driver instance and make sure logging is configured for our tests
    virtual void SetUp() {
        // Initialize logging
        initializeLogging();
        //liburb::EvHelper& evHelper = liburb::EvHelper::getInstance();
        conn = redis3m::async_connection::create("localhost", 6379);
        counter = 0;
    }

    // Truncate the log file at the end of every test and clean up any allocated driver objects.
    virtual void TearDown() {
    }

    ~RedisAsyncTest() {
        os::system("chmod -R a+w /tmp/test_redis");
    }
    
    redis3m::async_connection::ptr_t conn;
    int counter;
};

// Test driver functions by calling the methods and making sure log lines
// show up.
class MyCallback;
class MyCallback : public redis3m::async_callback, public std::enable_shared_from_this<MyCallback> {
public:
    MyCallback(redis3m::async_connection::ptr_t conn, int counter);
    inline void onReply(redisAsyncContext *, redis3m::reply&) {
        if (counter <= 0 && conn->is_valid()) {
            std::cout << "Disconnecting...\n";
            conn->disconnect();
            return;
        }
        //std::cout << "Am here!" << "\n";
        for (int i = 0; i < 2 && toschedule > 0; i++) {
            toschedule--;
            conn->execute(redis3m::command("RPUSH") << "mykey" << "myvalue", shared_from_this());
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
};

MyCallback::MyCallback(redis3m::async_connection::ptr_t _conn, int _counter) :
    counter(_counter), toschedule(_counter), conn(_conn) {
}

// Test the first constructor
TEST_F(RedisAsyncTest,Simple) {
    std::shared_ptr<MyCallback> cb = std::make_shared<MyCallback>(conn, 1000000);
    conn->execute(redis3m::command("RPUSH") << "mykey2" << "myvalue", cb);
    ev_loop(ev_default_loop(0), 0);
}

