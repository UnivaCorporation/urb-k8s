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

using std::cerr;
using std::cout;
using std::endl;
using std::flush;
using std::string;
using std::vector;


static bool loggingInitialized = false;
class RedisAsyncTest : public testing::Test {
protected:  // You should make the members protected s.t. they can be
    // accessed from sub-classes.

    // First time through clean up any existing log directory and set up
    // glog.
    void initializeLogging() {
        if (! loggingInitialized) {
            os::system("rm -rf /tmp/test_prog");
            os::system("mkdir /tmp/test_prog");
            FLAGS_log_dir = "/tmp/test_prog";
            google::InitGoogleLogging("test_prog");
            loggingInitialized = true;
            LOG(INFO) << "Initializing logging.";
        }
    }

    // Make a driver instance and make sure logging is configured for our tests
    virtual void SetUp() {
        // Initialize logging
        initializeLogging();
    }

    // Truncate the log file at the end of every test and clean up any allocated driver objects.
    virtual void TearDown() {
    }

    ~RedisAsyncTest() {
        os::system("chmod -R a+w /tmp/test_prog");
    }
};

// Test the first constructor
TEST_F(RedisAsyncTest,Simple) {
    //MyCallback cb(conn,1000000);
    //conn->execute(redis3m::command("RPUSH") << "mykey" << "myvalue",&cb);
    //ev_loop(EV_DEFAULT_ 0);
    cout << "Didn't crash!";
}

