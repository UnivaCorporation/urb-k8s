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


from __future__ import print_function

import re
import os
import os.path
import stat
import sys
import signal
import time
import gevent
#import gc
from gevent import event
from exceptions import KeyboardInterrupt
from optparse import OptionParser

from urb.exceptions.configuration_error import ConfigurationError
from urb.config.config_manager import ConfigManager
from urb.log.log_manager import LogManager
from urb.service.master_elector import MasterElector
from urb.messaging.channel_factory import ChannelFactory
from urb.messaging.channel import Channel
try:
    from urb import __version__
except:
    __version__ = "development"

class URBService:
    """ URB service class. """

    SECONDS_TO_WAIT_FOR_GREENLETS = 3
    GREENLET_SLEEP_PERIOD_IN_SECONDS = 0.001
    SHUTDOWN_EVENT_WAIT_PERIOD_IN_SECONDS = 30.0

    def __init__(self, defaults={}, skip_cmd_line_config=False):
        self.server = None
        self.shutdown = False
        self.shutdown_event = gevent.event.Event()

        # Config manager
        ConfigManager.get_instance().set_config_defaults(defaults)

        # Options
        self.option_parser = OptionParser()
        self.options = {}
        self.args = []
        if not skip_cmd_line_config:
            self.option_parser.add_option('-d', action="store_true",
                dest='daemon_flag', help="Run service as a daemon")
            self.option_parser.add_option('-p', '--pidfile',
                dest='pid_file', default=None,
                help="Store PID in the specified file")
            self.option_parser.add_option('-s', '--silent', action="store_true",
                dest='silent', help="No logging to stdout")
            self.parse_options()
            if self.get_daemon_flag() or self.get_silent():
                # Disable screen logging.
                ConfigManager.get_instance().set_console_log_level('notset')

        # Logger
        self.logger = LogManager.get_instance().get_logger('URBService')
        self.logger.info("Starting URB service version: %s" % __version__)
        # Configuration
        self.configure()

        # Signal handlers
        if not skip_cmd_line_config:
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGUSR1, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)

    def add_option(self, *args, **kwargs):
        self.option_parser.add_option(*args, **kwargs)
        self.parse_options()

    def parse_options(self):
        try:
            (self.options, self.args) = self.option_parser.parse_args()
            return (self.options, self.args)
        except SystemExit, rc:
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(int(str(rc)))

    def get_daemon_flag(self):
        return self.options.daemon_flag

    def get_pid_file(self):
        return self.options.pid_file

    def get_silent(self):
        return self.options.silent

    def configure(self):
        cm = ConfigManager.get_instance()

        config_items = cm.get_config_items('Service')
        self.handler_list = []
        try:
            for (key,value) in config_items:
                if key.endswith('_handler') and value is not None:
                    handler_module = value.split('.')[0]
                    handler_constructor = '.'.join(value.split('.')[1:])
                    handler_class = handler_constructor.split('(')[0]
                    self.logger.info('Instantiating handler: %s, handler_module=%s ,handler_class=%s'
                                     % (handler_constructor, handler_module ,handler_class))
                    exec('from %s import %s' % (handler_module,
                        handler_class))
                    exec('handler = %s' % (handler_constructor))
                    handler.register_shutdown_callback(self.shutdown_callback)
                    self.handler_list.append(handler)

        except Exception as ex:
            self.logger.error('URBService configuration error: %s' % ex)
            raise ConfigurationError(exception=ex)

        if len(self.handler_list) == 0:
            raise ConfigurationError(
                'URBService configuration error: At least one interface handler must be configured.')

    def remove_pid_file(self, pid_file=None):
        if pid_file and os.path.exists(pid_file):
            try:
                os.unlink(pid_file)
            except Exception as ex:
                print('Cannot remove pid file %s: %s' % (pid_file, ex), file=sys.stderr)
    
    def run(self):
        """ Run server. """
        options, args = self.parse_options()
        pid_file_name = self.get_pid_file()
        if self.get_daemon_flag():
            self.start_daemon_process(pid_file_name)
        try:
            self.serve_forever()
        except Exception as ex:
            print('Service exiting after unexpected error: %s ' % (ex), file=sys.stderr) 
            self.remove_pid_file(pid_file_name)
        self.logger.info("URB service exited\n\n\n")


    def start_daemon_process(self, pid_file_name):
        """ Run server in daemon mode. """
        # First fork: allow shell to return, detach from controlling 
        # terminal using setsid()
        try: 
            pid = gevent.fork()
            if pid > 0:
                sys.exit(0) 
        except OSError, e: 
            print('First fork failed with error %d (%s)' % (e.errno, e.strerror), file=sys.stderr)
            sys.exit(1)

        # Change directory to root, close original streams.
        os.chdir('/')
        os.setsid()
        os.umask(0)
        os.close(sys.stdin.fileno())
        os.close(sys.stdout.fileno())
        os.close(sys.stderr.fileno())

        # Second fork: setsid() makes you a session leader (can open
        # terminal session), and the fork makes you not a session leader and
        # prevents from accidentally reacquiring a controlling terminal.
        try: 
            pid = gevent.fork()
            if pid > 0:
                if pid_file_name is not None:
                    # Print pid before exit from second parent 
                    pid_file = open(pid_file_name, 'w')
                    print(pid, file= pid_file)
                    pid_file.close()
                    os.chmod(pid_file_name, 
                        stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
                sys.exit(0) 
        except OSError, e: 
            print('Second fork failed with error %d (%s)' % (e.errno, e.strerror), file=sys.stderr)
            self.remove_pid_file(pid_file_name)
            sys.exit(1) 

    def serve(self, time_in_seconds=0):
        start_time = time.time()
        end_time = None
        wait_time = URBService.SHUTDOWN_EVENT_WAIT_PERIOD_IN_SECONDS
        if time_in_seconds > 0:
            end_time = start_time + time_in_seconds
            # Configure the wait seconds based on our constant and the time_in_seconds parameter
            if time_in_seconds < wait_time:
                wait_time = time_in_seconds

        # Master elector
        master_elector = MasterElector(self.elected_master_callback,self.demoted_callback)
        master_elector.start()


        self.logger.info('Serving requests')
        while True:
            if self.shutdown:
                self.logger.debug("Shutdown flag was set")
                break
            if end_time is not None:
                now = time.time()
                if now > end_time:
                    self.logger.info('Done serving requests')
                    break
            self.logger.debug("serve: waiting for shutdown event for %d sec" % wait_time)
            self.shutdown_event.wait(wait_time)
            #gevent.sleep(URBService.GREENLET_SLEEP_PERIOD_IN_SECONDS)
        master_elector.stop()
#        gevent.killall([obj for obj in gc.get_objects() if isinstance(obj, gevent.Greenlet)])
        self.logger.info('Serving done')

    def serve_forever(self):
        self.serve()

    def elected_master_callback(self):
        self.logger.info('We have been elected the master')
        for handler in self.handler_list:
            self.logger.debug('Promoting handler: %s' % handler)
            handler.elected_master_callback()

    def demoted_callback(self):
        self.logger.info('We are no longer the master')
        for handler in self.handler_list:
            self.logger.debug('Demoted handler: %s' % handler)
            handler.demoted_callback()

    def shutdown_callback(self, request=None):
        self.logger.info('Service shutting down')
        self.demoted_callback()
        # wailt for all channel loops to exit
        gevent.sleep(Channel.MESSAGE_WAIT_PERIOD_IN_SECONDS)
        self.shutdown = True
        self.shutdown_event.set()
#        self.demoted_callback()
        ChannelFactory.get_instance().refresh_master_message_broker(ttl=0)

    def signal_handler(self, signal, frame):
        self.logger.info('Received signal %s' % signal)
        gevent.spawn(self.shutdown_callback)
    
# Run server.
def run():
    try:
#        from gevent import monkey; monkey.patch_socket()
        from gevent import monkey; monkey.patch_all()
        server = URBService()
        server.run()
    except KeyboardInterrupt as ex:
        pass
            
# Testing
if __name__ == '__main__':
    run()
 


