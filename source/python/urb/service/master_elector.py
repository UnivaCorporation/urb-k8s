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


import gevent
from gevent import event
import time
from urb.log.log_manager import LogManager
from urb.messaging.channel_factory import ChannelFactory
import socket
import os

class MasterElector(object):
    """ Master Elector class. """

    ELECTOR_SLEEP_PERIOD_IN_SECONDS = 15
    ELECTOR_TTL_IN_SECONDS = 60

    def __init__(self,elected_callback=None,demoted_callback=None):
        self.__run = False
        self.__master_broker = None
        self.__set_server_id()
        self.__thread_event = gevent.event.Event()

        self.logger = LogManager.get_instance().get_logger(
            self.__class__.__name__)

        self.elected_callback = elected_callback
        self.demoted_callback = demoted_callback

    def __set_server_id(self):
        self.__hostname = socket.gethostname()
        self.__server_id = self.__hostname + "." + str(os.getpid())

    def elect(self):
        """ Monitoring thread. """
        self.logger.debug('MasterElector: Entering election loop')
        cf = ChannelFactory.get_instance()
        while True:
            if not self.__run:
                break
            self.__thread_event.clear()
            were_mb = self.is_master_message_broker()

            try:
                self.__master_broker = cf.determine_master_message_broker(value=self.__server_id,ttl=MasterElector.ELECTOR_TTL_IN_SECONDS)
            except Exception, ex:
                self.logger.error("MasterElector: Error determining master broker: %s" % ex)
                self.__thread_event.wait(MasterElector.ELECTOR_SLEEP_PERIOD_IN_SECONDS)
                continue

            self.logger.debug("The current master broker is: %s" % self.__master_broker)

            if self.is_master_message_broker():
                # We are the master broker... lets make sure that our ttl is updated
                self.logger.debug("MasterElector: we are master broker")
                try:
                    cf.refresh_master_message_broker(ttl=MasterElector.ELECTOR_TTL_IN_SECONDS)
                except Exception, ex:
                    self.logger.error("MasterElector: Unable to refresh the master broker: %s" % ex)

                # We are now and if we weren't before trigger the callback
                if not were_mb and self.elected_callback:
                    try:
                        self.elected_callback()
                        self.logger.debug("MasterElector: Elected callback complete.")
                    except Exception, ex:
                        self.logger.warn("MasterElector: Exception calling demote callback")
                        self.logger.exception(ex)
            else:
                # We aren't the master broker.  If we were before lets call the demote callback
                self.logger.debug("MasterElector: we are not master broker")
                if were_mb and self.demoted_callback:
                    try:
                        self.demoted_callback()
                    except Exception, ex:
                        self.logger.warn("MasterElector: Exception calling demote callback")
                        self.logger.exception(ex)

            # Monitoring thread sleep
            self.logger.debug("MasterElector: sleeping for %d sec" % MasterElector.ELECTOR_SLEEP_PERIOD_IN_SECONDS)
            self.__thread_event.wait(MasterElector.ELECTOR_SLEEP_PERIOD_IN_SECONDS)

        self.logger.debug('MasterElector: Exiting election loop')

    def is_master_message_broker(self):
        """ Return's true if this is the master message broker """
        return self.__server_id == self.__master_broker

    def stop(self):
        """ Stop Election process. """
        self.__run = False
        self.__thread_event.set()
        self.__elect_thread.join()
        
    def start(self):
        """ Start Election process. """
        self.__set_server_id()
        self.__run = True
        self.__elect_thread = gevent.spawn(self.elect)
        return self.__elect_thread

# Testing
if __name__ == '__main__':
    import time
    me = MasterElector()
    me.start()
    t1 = time.time()
    gevent.sleep(20)
    me.stop()
    t2 = time.time()
    print "This test should have taken exactly 20 seconds.  It took: %d" % (t2-t1)

