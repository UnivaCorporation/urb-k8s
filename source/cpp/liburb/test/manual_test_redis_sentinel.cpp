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
#include <redis3m/async_connection_pool.h>
#include <async.h>
#include <ev.h>
#include <gtest/gtest.h>
#include <stout/os.hpp>
#include <glog/logging.h>

using std::cerr;
using std::cout;
using std::endl;
using std::flush;
using std::string;
using std::vector;


// To use a test fixture, derive a class from testing::Test.
static bool loggingInitialized = false;
class RedisSentinelTest : public testing::Test {
protected:  // You should make the members protected s.t. they can be
    // accessed from sub-classes.

    // First time through clean up any existing log directory and set up
    // glog.
    void initializeLogging() {
        if (!loggingInitialized) {
            os::system("rm -rf /tmp/test_redis_sentinel");
            os::system("mkdir /tmp/test_redis_sentinel");
            FLAGS_log_dir = "/tmp/test_redis_sentinel";
            google::InitGoogleLogging("test_redis_sentinel");
            loggingInitialized = true;
            DLOG(INFO) << "Initializing logging.";
        }
    }

    // Make a driver instance and make sure logging is configured for our tests
    virtual void SetUp() {
        // Initialize logging
        initializeLogging();
        pool = redis3m::async_connection_pool::create("head.private:8080,localhost,a.b.c:junk", "mymaster");
        counter = 0;
    }

    // Truncate the log file at the end of every test and clean up any allocated driver objects.
    virtual void TearDown() {
    }

    ~RedisSentinelTest() {
        os::system("chmod -R a+w /tmp/test_redis_sentinel");      
    }
    redis3m::async_connection_pool::ptr_t pool;
    int counter;
};

// Test driver functions by calling the methods and making sure log lines
// show up.
class MyCallback;
class MyCallback : public redis3m::async_callback, public std::enable_shared_from_this<MyCallback> {
public:
    MyCallback(redis3m::async_connection::ptr_t conn, int counter);
    inline void onReply(redisAsyncContext */*c*/, redis3m::reply& /*reply*/) {
        if (counter <= 0 && conn->is_valid()) {
            conn->disconnect();
            return;
        }
        //std::cout << "Am here!" << "\n";
        for (int i =0; i < 2 && toschedule > 0; i++) {
            toschedule--;
            conn->execute(redis3m::command("RPUSH") << "mykey" << "myvalue", shared_from_this());
        }
        counter--;
        if (counter % 100 == 0) {
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
TEST_F(RedisSentinelTest,Simple) {
    redis3m::async_connection::ptr_t conn = pool->get();
    redis3m::async_connection::ptr_t conn2 = pool->get();
    ASSERT_TRUE(conn->is_valid());
    ASSERT_TRUE(conn != conn2);
    std::shared_ptr<MyCallback> cb = std::make_shared<MyCallback>(conn, 1000);
    conn->execute(redis3m::command("RPUSH") << "mykey2" << "myvalue", cb);
    ev_loop(ev_default_loop(0), 0);
}

