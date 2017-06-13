#!/usr/bin/env python

# Copyright 2017 Univa Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import threading

class ObjectTracker(object):

    # Singleton
    __instance_lock = threading.RLock()
    __instance = None

    def __new__(cls, *args, **kwargs):
        ObjectTracker.__instance_lock.acquire()
        try:
            # Allow subclasses to create their own instances.
            if cls.__instance is None or cls != type(cls.__instance):
                cls.__instance = object.__new__(cls, *args, **kwargs)
                cls.__instance.__init__()
            return cls.__instance
        finally:
            ObjectTracker.__instance_lock.release()

    @classmethod
    def get_instance(cls, *args, **kwargs):
        return cls.__new__(cls, *args, **kwargs)

    def __init__(self):
        self.lock = threading.RLock()
        self.object_dict = {}

    def add(self, id, object):
        self.object_dict[id] = object

    def get(self, id):
        return self.object_dict.get(id)

    def remove(self, id):
        object = self.object_dict.get(id)
        if object is not None:
            del self.object_dict[id]
        return object

    def __iter__(self):
        return self.object_dict.iteritems()

    def keys(self):
        return self.object_dict.keys()

# Testing
if __name__ == '__main__':
    ot = ObjectTracker.get_instance()
    ot.add(1, 'a')
    ot.add(2, 'b')
    print ot 
    print ot.keys()

