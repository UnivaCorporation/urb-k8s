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
#include <chrono>


#include <ctime>


#include <gtest/gtest.h>
#include <glog/logging.h>
#include <stout/os.hpp>
#include "timer.hpp"

#include <json_protobuf.h>
#include "timer.hpp"
#include <mesos.pb.h>

using std::cerr;
using std::cout;
using std::endl;
using std::flush;
using std::string;
using std::vector;


static bool loggingInitialized = false;
class TimerTest : public testing::Test {
protected:  // You should make the members protected s.t. they can be
    // accessed from sub-classes.

    // First time through clean up any existing log directory and set up
    // glog.
    void initializeLogging() {
        if (! loggingInitialized) {
            os::system("rm -rf /tmp/test_timer");
            os::system("mkdir /tmp/test_timer");
            FLAGS_log_dir = "/tmp/test_timer";
            google::InitGoogleLogging("test_timer");
            loggingInitialized = true;
            DLOG(INFO) << "Initializing logging.";
        }
    }


    // Make a driver instance and make sure logging is configured for our tests
    virtual void SetUp() {
        // Initialize logging
        initializeLogging();
        rTimer = new liburb::Timer<TimerTest>(this);
        counter = 0;
    }

    // Truncate the log file at the end of every test and clean up any allocated driver objects.
    virtual void TearDown() {
        delete rTimer;
    }

    ~TimerTest() {
        os::system("chmod -R a+w /tmp/test_timer");
    }
    liburb::Timer<TimerTest> *rTimer;
    std::chrono::system_clock::time_point callback_time;
    int counter;
//    const liburb::centiseconds accuracy = liburb::centiseconds(10);
//    const liburb::timer_time_point::duration accuracy = liburb::timer_time_point::duration(2);
    const liburb::timer_time_point::duration accuracy = liburb::timer_time_point::duration(2);
    public:
    void testDelay(const liburb::timer_time_point::duration& cb_delay, const liburb::timer_time_point::duration& sleep_delay, liburb::Timer<TimerTest> &timer);
    void cb();
    void cbr();
    void cbm();
};

std::ostream &operator<<(std::ostream &s, const std::chrono::system_clock::time_point &t) {
    return s << std::chrono::time_point_cast<liburb::timer_time_point::duration>(t).time_since_epoch().count();
}

void TimerTest::cb() {
    callback_time = std::chrono::system_clock::now();
    cout << "In test callback " /*<< callback_time*/ << endl;
}

void TimerTest::cbm() {
    cout << "In test callback m counter [" << counter << "]" << endl;
    counter++;
}

void TimerTest::cbr() {
   cout << "In test callback r, (counter=" << counter << ")" << endl;
   if (counter < 10) {
//      cout << "Calling delay again (counter=" << counter <<")" << endl;
      rTimer->delay(std::chrono::duration_cast<liburb::timer_time_point::duration>(std::chrono::seconds(1)), &TimerTest::cbr);
   }
   counter++;
//   cout << "Exiting test callback r (counter=" << counter <<")" << endl;
}

void TimerTest::testDelay(const liburb::timer_time_point::duration& cb_delay,
                          const liburb::timer_time_point::duration& sleep_delay,
                          liburb::Timer<TimerTest>& timer) {
    timer.delay(cb_delay, &TimerTest::cb);
    std::this_thread::sleep_for(sleep_delay);
    std::chrono::system_clock::time_point t = std::chrono::system_clock::now();
//    cout << "After delay:      " << t << endl;
    auto extra_wait = std::chrono::duration_cast<liburb::timer_time_point::duration>(t - callback_time);
    cout << "Delay: extra_wait=" << extra_wait.count()
         << ", callback_requested=" << cb_delay.count()
         << ", sleep=" << sleep_delay.count() << endl;
    ASSERT_GT(cb_delay + extra_wait, sleep_delay - accuracy);
    ASSERT_LT(cb_delay + extra_wait, sleep_delay + accuracy);
}

// Test the first constructor
TEST_F(TimerTest,Simple) {
   liburb::Timer<TimerTest> *t = new liburb::Timer<TimerTest>(this);
   delete t;
}

// Now test a delay call
TEST_F(TimerTest,Delay1) {
    const liburb::centiseconds cb_delay(100);
    const liburb::centiseconds sleep_delay(300);
    liburb::Timer<TimerTest> *t = new liburb::Timer<TimerTest>(this);
    testDelay(std::chrono::duration_cast<liburb::timer_time_point::duration>(cb_delay),
              std::chrono::duration_cast<liburb::timer_time_point::duration>(sleep_delay),
              *t);
    delete t;
}

TEST_F(TimerTest,RDelay1) {
    cbr();
    for(int i=0; i < 30; i++) {
        if(counter >= 10)
        {
           //cout << "RDelay1: counter=" << counter << ", break" << endl;
           break;
        }
        //cout << "RDelay1: counter=" << counter << ", sleeping" << endl;
        sleep(1);
    }
    ASSERT_EQ(counter,10);
}

// Now test a delay call
TEST_F(TimerTest,Delay2) {
    const std::chrono::milliseconds cb_delay(1000);
    const std::chrono::milliseconds sleep_delay(3000);
    liburb::Timer<TimerTest> *t = new liburb::Timer<TimerTest>(this);
    testDelay(std::chrono::duration_cast<liburb::timer_time_point::duration>(cb_delay),
              std::chrono::duration_cast<liburb::timer_time_point::duration>(sleep_delay),
              *t);
    delete t;
}


// Now test a rerun...
TEST_F(TimerTest,Delay3) {
    const std::chrono::milliseconds cb_delay(1000);
    const std::chrono::milliseconds sleep_delay(3000);
    liburb::Timer<TimerTest> timer(this);
    for (int i=0; i< 10; i++) {
        testDelay(std::chrono::duration_cast<liburb::timer_time_point::duration>(cb_delay),
                  std::chrono::duration_cast<liburb::timer_time_point::duration>(sleep_delay),
                  timer);
    }
}

// Now test a cancel call
TEST_F(TimerTest,Cancel1) {
    const std::chrono::seconds sleep_delay(2);
    liburb::Timer<TimerTest> *timer = new liburb::Timer<TimerTest>(this);
    // no callcack expected
    callback_time = std::chrono::system_clock::now();
    Try<Seconds> d(1);
    timer->delay(d.get(), &TimerTest::cb);
    timer->cancel();
    std::this_thread::sleep_for(std::chrono::seconds(sleep_delay));
    std::chrono::system_clock::time_point t = std::chrono::system_clock::now();
    auto actual_delay_ms = std::chrono::duration_cast<std::chrono::milliseconds>(t - callback_time).count();
    LOG(INFO) << "Delay: " << actual_delay_ms << " ms" << endl;
    ASSERT_GT(actual_delay_ms, (sleep_delay - accuracy).count());
    delete timer;
}

// Finally test lots of timers
// Now test a cancel call
TEST_F(TimerTest,Many) {
    constexpr int CNT = 100;
    liburb::Timer<TimerTest>* timers[CNT];   
    for (int i = 0; i < CNT; i++) {
       timers[i] = new liburb::Timer<TimerTest>(this);
       Try<Duration> d = Seconds(i%10+1);
       timers[i]->delay(d.get(), &TimerTest::cbm);
   }
   for (int i = 0; i < 30; i++) {
      if(counter >= CNT) break;
      sleep(1);
   }
   ASSERT_EQ(counter,CNT);
   for (int i = 0; i < CNT; i++) {
       delete timers[i];
   }
}

