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


#ifndef __EVHELPER_HPP__
#define __EVHELPER_HPP__

#include <ev.h>
#include <thread>
#include <mutex>
#include <memory>
#include <map>
#include <list>
#include <chrono>

namespace liburb {

using centi = std::ratio<1l, 100l>;
using deci = std::ratio<1l, 10l>;
using centiseconds = std::chrono::duration<long long, centi>;
using deciseconds = std::chrono::duration<long long, deci>;
using timer_duration = deciseconds;
//using timer_duration = std::chrono::seconds;
using timer_time_point = std::chrono::time_point<std::chrono::system_clock, timer_duration>;

class TimerBase;

class EvHelper
{
public:
  static EvHelper& getInstance();
  std::mutex& getMutex();
  static struct ev_loop* getLoop();
  void scheduleTimer(std::shared_ptr<TimerBase> t);
  void refresh();
  void shutdown();
  bool isLoopExited();
  ~EvHelper();
  static void timeout_cb(EV_P_ ev_timer *w, int revents);

private:
  EvHelper();
  EvHelper(const EvHelper& eh);
  static void async_cb(EV_P_ ev_async *w, int revents);
  void eventLoop();

  static std::mutex loop_mutex;
  static struct ev_loop* loop;
  ev_async async_w;
  static ev_timer timeout_watcher;
  std::thread eventLoopThread;
  static std::map<timer_time_point, std::list<std::shared_ptr<TimerBase>>> timers;
  static bool enabled;
  bool loopExited;
};

class TimerBase {
public:
    TimerBase() : evHelper(EvHelper::getInstance()), active(false) {}
    virtual ~TimerBase() {}
    virtual void executeMethod() = 0;
    EvHelper& getEvHelper() { return evHelper; }
    bool getActive() { return active; }
    timer_time_point getFireTime() { return fireTime; }
protected:
    timer_time_point fireTime;
    EvHelper& evHelper;
    bool active;
};

} // namespace liburb {

#endif // __EVHELPER_HPP__
