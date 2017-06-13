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
#include "url.hpp"

using std::cerr;
using std::cout;
using std::endl;
using std::flush;
using std::string;
using std::vector;


static bool loggingInitialized = false;
class UrlParseTest : public testing::Test {
protected:  // You should make the members protected s.t. they can be
    // accessed from sub-classes.

    // First time through clean up any existing log directory and set up
    // glog.
    void initializeLogging() {
        if (!loggingInitialized) {
            os::system("rm -rf /tmp/test_url");
            os::system("mkdir /tmp/test_url");
            FLAGS_log_dir = "/tmp/test_url";
            google::InitGoogleLogging("test_url");
            loggingInitialized = true;
            DLOG(INFO) << "Initializing logging.";
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

    ~UrlParseTest() {
        os::system("chmod -R a+w /tmp/test_url");
    }
};

// Test the first constructor
TEST_F(UrlParseTest,Simple) {
    std::string url = "urb://localhost";
    Try<liburb::URL> parsed_url = liburb::URL::parse(url);
    ASSERT_FALSE(parsed_url.isError());
    ASSERT_EQ(parsed_url.get().servers, "localhost");
    ASSERT_EQ(parsed_url.get().ha, false);
    ASSERT_EQ(parsed_url.get().path, "/");
    ASSERT_EQ(parsed_url.get().credentials, "");
}

TEST_F(UrlParseTest,SimpleFqdn) {
    std::string url = "urb://h1h2h3h4.private.com";
    Try<liburb::URL> parsed_url = liburb::URL::parse(url);
    ASSERT_FALSE(parsed_url.isError());
    ASSERT_EQ(parsed_url.get().servers, "h1h2h3h4.private.com");
    ASSERT_EQ(parsed_url.get().ha, false);
    ASSERT_EQ(parsed_url.get().path, "/");
    ASSERT_EQ(parsed_url.get().credentials, "");
}

TEST_F(UrlParseTest,Port) {
    std::string url = "urb://localhost:8080";
    Try<liburb::URL> parsed_url = liburb::URL::parse(url);
    ASSERT_FALSE(parsed_url.isError());
    ASSERT_EQ(parsed_url.get().servers, "localhost:8080");
    ASSERT_EQ(parsed_url.get().ha, false);
    ASSERT_EQ(parsed_url.get().path, "/");
    ASSERT_EQ(parsed_url.get().credentials, "");
}

TEST_F(UrlParseTest,User) {
    std::string url = "urb://bob@localhost";
    Try<liburb::URL> parsed_url = liburb::URL::parse(url);
    ASSERT_FALSE(parsed_url.isError());
    ASSERT_EQ(parsed_url.get().servers, "localhost");
    ASSERT_EQ(parsed_url.get().ha, false);
    ASSERT_EQ(parsed_url.get().path, "/");
    ASSERT_EQ(parsed_url.get().credentials, "bob");
}

TEST_F(UrlParseTest,UserPass) {
    std::string url = "urb://bob:pass@localhost";
    Try<liburb::URL> parsed_url = liburb::URL::parse(url);
    ASSERT_FALSE(parsed_url.isError());
    ASSERT_EQ(parsed_url.get().servers, "localhost");
    ASSERT_EQ(parsed_url.get().ha, false);
    ASSERT_EQ(parsed_url.get().path, "/");
    ASSERT_EQ(parsed_url.get().credentials, "bob:pass");
}

TEST_F(UrlParseTest,UserPassPort) {
    std::string url = "urb://bob:pass@localhost:8080";
    Try<liburb::URL> parsed_url = liburb::URL::parse(url);
    ASSERT_FALSE(parsed_url.isError());
    ASSERT_EQ(parsed_url.get().servers, "localhost:8080");
    ASSERT_EQ(parsed_url.get().ha, false);
    ASSERT_EQ(parsed_url.get().path, "/");
    ASSERT_EQ(parsed_url.get().credentials, "bob:pass");
}

TEST_F(UrlParseTest,UserPassPortPath) {
    std::string url = "urb://bob:pass@localhost:8080/apath";
    Try<liburb::URL> parsed_url = liburb::URL::parse(url);
    ASSERT_FALSE(parsed_url.isError());
    ASSERT_EQ(parsed_url.get().servers, "localhost:8080");
    ASSERT_EQ(parsed_url.get().ha, false);
    ASSERT_EQ(parsed_url.get().path, "/apath");
    ASSERT_EQ(parsed_url.get().credentials, "bob:pass");
}

TEST_F(UrlParseTest,UserPassPortPath2) {
    std::string url = "urb://bob:pass@localhost:8080/apath/andanother";
    Try<liburb::URL> parsed_url = liburb::URL::parse(url);
    ASSERT_FALSE(parsed_url.isError());
    ASSERT_EQ(parsed_url.get().servers, "localhost:8080");
    ASSERT_EQ(parsed_url.get().ha, false);
    ASSERT_EQ(parsed_url.get().path, "/apath/andanother");
    ASSERT_EQ(parsed_url.get().credentials, "bob:pass");
}

TEST_F(UrlParseTest,UserPassPortPathMultiNoHA) {
    std::string url = "urb://bob:pass@localhost:8080,host2,host3:6060/apath";
    Try<liburb::URL> parsed_url = liburb::URL::parse(url);
    //Should be an error since we don't support non ha multi-host
    ASSERT_TRUE(parsed_url.isError());
}

TEST_F(UrlParseTest,UserPassPortPathMulti) {
    std::string url = "urb://ha://bob:pass@localhost:8080,host2,host3:6060/apath";
    Try<liburb::URL> parsed_url = liburb::URL::parse(url);
    ASSERT_FALSE(parsed_url.isError());
    ASSERT_EQ(parsed_url.get().servers, "localhost:8080,host2,host3:6060");
    ASSERT_EQ(parsed_url.get().ha, true);
    ASSERT_EQ(parsed_url.get().path, "/apath");
    ASSERT_EQ(parsed_url.get().credentials, "bob:pass");
}

