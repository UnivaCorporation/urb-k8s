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


#ifndef __TIMER_HPP__
#define __TIMER_HPP__

#include <iostream>
#include <ev.h>
#include <stout/duration.hpp>
#include <thread>
#include <memory>
#include <glog/logging.h>

#include "evhelper.hpp"

namespace liburb {

template <typename T>
class Timer : public TimerBase
{
public:
  Timer(T* _target) : target(_target), method(nullptr) {}
  ~Timer() {
      //Make sure we mark our inner as inactive...
      cancel();
  }

  void delay(const Duration& _duration, void(T::*_method)()) {
      if (!active) {
          inner = std::make_shared<Timer<T>>(target);
          inner->method = _method;
          int64_t ns = _duration.ns();
          std::chrono::nanoseconds dns(ns);
          std::chrono::system_clock::time_point t = std::chrono::system_clock::now();
          inner->fireTime = std::chrono::time_point_cast<timer_time_point::duration>(t + dns);
          VLOG(3) << "Timer::delay(): fireTime=" << inner->fireTime.time_since_epoch().count();
          inner->active = true;
          evHelper.scheduleTimer(inner);
      }
  }

  void delay(const timer_time_point::duration& _duration, void(T::*_method)()) {
      if (!active) {
          inner = std::make_shared<Timer<T>>(target);
          inner->method = _method;
          inner->fireTime = std::chrono::time_point_cast<timer_time_point::duration>(std::chrono::system_clock::now()) + _duration;
          VLOG(3) << "Timer::delay(): fireTime=" << inner->fireTime.time_since_epoch().count();
          inner->active = true;
          evHelper.scheduleTimer(inner);
      }
  }

  void executeMethod() {
      if (!active) {
          //This timer has been cancelled... return.
          return;
      }
      active = false;
      if (method != nullptr) {
          (*target.*method)();
      }
  }

  void cancel() {
       active = false;
       if (inner != nullptr) {
           inner->active = false;
       }
  }

private:
  T *target;
  std::shared_ptr<Timer<T>> inner;
  void (T::*method)();
};


} // namespace liburb {

#endif // __TIMER_HPP__

