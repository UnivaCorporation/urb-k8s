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


import os
import os.path
import sys
import subprocess
import socket
from tempfile import NamedTemporaryFile

from nose import SkipTest
from nose.tools import make_decorator

REDIS_HOST = "localhost"
REDIS_PORT = 6379

LOG_FILE = '/tmp/urb.test.log'


def run_command(command, **kwargs):
#    logger.debug( "runCommand: command [%s], kwargs [%s]" % (command, kwargs))
    kwargs['shell'] = True
    capture_stdout = False
    capture_stderr = False
    if not kwargs.has_key('stdout'):
        kwargs["stdout"] = subprocess.PIPE
        capture_stdout = True
    if not kwargs.has_key('stderr'):
        kwargs["stderr"] = subprocess.PIPE
        capture_stderr = True

    p = subprocess.Popen(command, **kwargs)
    o = ("","")
    if capture_stdout or capture_stderr:
        o = p.communicate()
    if capture_stdout:
        sys.stdout.write(o[0])
    if capture_stderr:
        sys.stderr.write(o[1])
    return (p,o)

def remove_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)

def remove_test_log_file():
    remove_file(LOG_FILE)

def remove_test_config_file():
    remove_file(URB_CONFIG_FILE)

def read_last_line(file_path):
    f = open(file_path, 'r')
    last_line = None
    while True:
        line = f.readline()
        if not line:
            break
        last_line = line
    f.close()
    return last_line

def read_last_log_line():
    return read_last_line(LOG_FILE)

# Service utilities
def create_config_manager():
    from urb.config.config_manager import ConfigManager
    cm = ConfigManager.get_instance()
    print "set log file to %s" % LOG_FILE
    cm.set_log_file(LOG_FILE)
    cm.set_file_log_level('trace')

def create_service_thread(serve_time=10):
    from gevent import monkey
    monkey.patch_socket() 
    monkey.patch_thread() 
    from threading import Thread
    from urb.service.urb_service import URBService
    create_config_manager()
    class ServiceThread(Thread):
        def run(self):
            self.urb_service = URBService(skip_cmd_line_config=True)
            self.urb_service.serve(serve_time)
    service_thread = ServiceThread()
    return service_thread

def create_service_channel(channel_name):
    from urb.messaging.channel_factory import ChannelFactory
    create_config_manager()
    return ChannelFactory.get_instance().create_channel(channel_name)

# Common decorators
def needs_setup(func):
    def inner(*args, **kwargs):
        return func(*args,**kwargs)
    return make_decorator(func)(inner)

def needs_cleanup(func):
    def inner(*args, **kwargs):
#        remove_test_files()
        return func(*args,**kwargs)
    return make_decorator(func)(inner)

def needs_config(func):
    def inner(*args,**kwargs):
        try:
            create_config_manager()
        except Exception, ex:
            print ex
            raise SkipTest("Config manager instance could not be created.")
        return func(*args,**kwargs)
    return make_decorator(func)(inner)

def needs_redis(func):
    def inner(*args,**kwargs):
        import redis
        v = ""
        try:
            r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
            v = r.echo("test")
        except:
            pass
        if v == "test":
            return func(*args,**kwargs)
        raise SkipTest("Redis is not available.")
    return make_decorator(func)(inner)

# Testing
if __name__ == '__main__':
    print 'Last line: ', read_last_line('/tmp/urb.log')

