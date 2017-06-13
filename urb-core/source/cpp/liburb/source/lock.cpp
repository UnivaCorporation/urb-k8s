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


#include "lock.hpp"

namespace mesos {
namespace internal {

Lock::Lock(pthread_mutex_t* _mutex)
  : mutex(_mutex), locked(false)
{
  lock();
}


void Lock::lock()
{
  if (!locked) {
    pthread_mutex_lock(mutex);
    locked = true;
  }
}


void Lock::unlock()
{
  if (locked) {
    locked = false;
    pthread_mutex_unlock(mutex);
  }
}


Lock::~Lock()
{
  unlock();
}

} // namespace internal {
} // namespace mesos {
