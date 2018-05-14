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
#include <list>
#include <glog/logging.h>
#include "evhelper.hpp"


namespace liburb {

ev_timer EvHelper::s_timeoutWatcher_;
bool EvHelper::s_enabled_ = true;
std::mutex EvHelper::s_loopMutex_;
struct ev_loop* EvHelper::s_loop_;
std::map<timer_time_point, std::list<std::shared_ptr<TimerBase>>> EvHelper::s_timers_;

class BaseTimer;

void EvHelper::timeout_cb(EV_P_ ev_timer *w, int /*revents*/) {
    timer_time_point::duration duration = std::chrono::duration_cast<timer_time_point::duration>(std::chrono::seconds(60));
    std::list<std::list<std::shared_ptr<TimerBase>>> callbacks;
    {
        VLOG(3) << "EvHelper::timeout_cb(): lock_guard in";
        std::lock_guard<std::mutex> lock(s_loopMutex_);
        if (!s_enabled_) {
            LOG(INFO) << "EvHelper::timeout_cb(): Ignoring timer callback since we are disabled";
            return;
        }
        timer_time_point now = std::chrono::time_point_cast<timer_time_point::duration>(std::chrono::system_clock::now());
        VLOG(3) << "EvHelper::timeout_cb(): list count: " << s_timers_.size() << ", time to first elem " << (s_timers_.begin()->first - now).count();
        if (!s_timers_.empty() && now >= s_timers_.begin()->first) {
            auto upper = s_timers_.upper_bound(now);
            for (auto iterator = s_timers_.begin(); iterator != upper; ++iterator) {
                callbacks.push_back(iterator->second);
            }
            s_timers_.erase(s_timers_.begin(), upper);
        }
        if (!s_timers_.empty()) {
            // Get the next fire time
            duration = s_timers_.begin()->first - now;
        }
        VLOG(3) << "EvHelper::timeout_cb(): next fire time in: " << duration.count() << ", lock_guard out";
    }
    // Now call the callbacks
    for (auto &lst: callbacks) {
        for (auto &timer: lst) {
            if (timer->getActive()) {
                VLOG(3) << "EvHelper::timeout_cb(): execute callback for: " << timer->getFireTime().time_since_epoch().count();
                timer->executeMethod();
            } else {
                VLOG(3) << "EvHelper::timeout_cb(): inactive: do not execute callback for:" << timer->getFireTime().time_since_epoch().count();
            }
        }
    }
    w->repeat = static_cast<ev_tstamp>(std::chrono::duration_cast<timer_time_point::duration>(duration).count())/timer_time_point::duration::period::den;
    ev_timer_again(loop, w);
}

EvHelper::EvHelper() : loopExited_(false) {
    VLOG(1) << "EvHelper::EvHelper()";
    s_loop_ = ev_loop_new(0);
    ev_async_init(&async_w_, EvHelper::async_cb);
    ev_async_start(s_loop_, &async_w_);

    // Fire up the timer handler
    ev_timer_init(&s_timeoutWatcher_, &timeout_cb, 0., 60.);
    ev_timer_start(s_loop_, &s_timeoutWatcher_);

    //Start the event thread
    eventLoopThread_ = std::thread(&EvHelper::eventLoop, this);
}

EvHelper::~EvHelper() {
    // The join is done here because this should never happen inside the event loop
    // thread.
    VLOG(1) << "EvHelper::~EvHelper()";
    ev_async_stop(s_loop_, &async_w_);
    ev_timer_stop(s_loop_, &s_timeoutWatcher_);
    shutdown();
    //CHECK(eventLoopThread.timed_join(std::posix_time::seconds(1)));
    //ev_loop_verify(loop);

    // Protection against malfunctioning framework implementations to avoid hanging on framework exit.
    // In case of Spark/Thunder under stringent conditions Java VM unexpectedly exits leaving
    // org_apache_mesos_MesosSchedulerDriver.cpp:JNIScheduler::resourceOffers to wait infinitely on
    // jvm->AttachCurrentThread() to nonexisting JVM which in turn makes ~EvHelper() hang on
    // eventLoopThread.join() on framework exit.
    for (int i = 0; i < 3; i++) {
        if (loopExited_) {
            VLOG(1) << "EvHelper::~EvHelper(): before join";
            eventLoopThread_.join();
            LOG(INFO) << "EvHelper::~EvHelper(): Event thread joined";
            ev_loop_destroy(s_loop_);
            VLOG(1) << "EvHelper::~EvHelper() end";
            return;
        }
        VLOG(1) << "EvHelper::~EvHelper(): sleeping";
        sleep(1);
    }
    LOG(ERROR) << "EvHelper::~EvHelper(): terminating: this may indicate malfunctioning mesos framework";
    std::terminate();
}

void EvHelper::eventLoop() {
    while (s_enabled_) {
        try {
            VLOG(4) << "EvHelper::eventLoop(): before ev_run";
            ev_run(s_loop_, EVRUN_ONCE);
            VLOG(4) << "EvHelper::eventLoop(): after ev_run";
        } catch (std::exception& e) {
            std::cout << "EvHelper::eventLoop: std::exception " << e.what() << "\n";
            LOG(ERROR) << "EvHelper::eventLoop: std::exception " << e.what();
            throw;
        }
        usleep(10);
    }
    loopExited_ = true;
    LOG(INFO) << "EvHelper::eventLoop: exiting event loop";
}

bool EvHelper::isLoopExited() {
    return loopExited_;
}

void EvHelper::refresh() {
    VLOG(3) << "EvHelper::refresh()";
    ev_async_send(s_loop_, &async_w_);
}

struct ev_loop* EvHelper::getLoop() {
    return s_loop_;
}

void EvHelper::async_cb(EV_P_ ev_async */*w*/, int /*revents*/) {
    VLOG(4) << "EvHelper::async_cb(): lock_guard in";
    std::lock_guard<std::mutex> lock(s_loopMutex_);
    if (!s_enabled_) {
        VLOG(1) << "EvHelper::async_cb: calling ev_break";
        // Unloop and shutdown
        //ev_unloop(ev.getLoop(),EVUNLOOP_ALL);
        ev_break(s_loop_, EVBREAK_ALL);
        return;
    }
    s_timeoutWatcher_.repeat = 0;
    ev_timer_again(s_loop_, &s_timeoutWatcher_);
    ev_feed_event(s_loop_, &s_timeoutWatcher_, EV_TIMEOUT);
    VLOG(4) << "EvHelper::async_cb() done: lock_guard out";
}


EvHelper& EvHelper::getInstance() {
    DLOG(INFO) << "EvHelper::getInstance";
    static EvHelper eh;
    return eh;
}

void EvHelper::scheduleTimer(std::shared_ptr<TimerBase> t) {
    VLOG(4) << "EvHelper::scheduleTimer(): lock_guard in";
    std::lock_guard<std::mutex> lock(s_loopMutex_);
    auto key = t->getFireTime();
    if (!s_timers_.count(key)) {
        VLOG(4) << "new TimerBase for key " << t->getFireTime().time_since_epoch().count() << std::endl;
        std::list<std::shared_ptr<TimerBase> > l;
        s_timers_[key] = l;
    }
    VLOG(4) << "push_back for key " << t->getFireTime().time_since_epoch().count() << std::endl;
    s_timers_[key].push_back(t);
    refresh();
    VLOG(4) << "EvHelper::scheduleTimer(): lock_guard out";
}

std::mutex& EvHelper::getMutex() {
      return s_loopMutex_;
}

void EvHelper::shutdown() {
    VLOG(1) << "EvHelper::shutdown()";
    s_enabled_ = false;
    // The refresh call will trigger a break if we are not being called from inside
    // the event thread. If we are in the event thread the loop will exit at the completion
    // of this event.
    if (eventLoopThread_.get_id() == std::this_thread::get_id()) {
      refresh();
    } else {
      VLOG(1) << "EvHelper::shutdown() called not from main thread";
    }
    VLOG(1) << "EvHelper::shutdown() end";
}

} // namespace liburb {
