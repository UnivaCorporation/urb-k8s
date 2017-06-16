#!/usr/bin/env python
# ___INFO__MARK_BEGIN__
# ############################################################################
#
# This code is the Property, a Trade Secret and the Confidential Information
#  of Univa Corporation.
#
#  Copyright Univa Corporation. All Rights Reserved. Access is Restricted.
#
#  It is provided to you under the terms of the
#  Univa Term Software License Agreement.
#
#  If you have any questions, please contact our Support Department.
#
#  www.univa.com
#
###########################################################################
#___INFO__MARK_END__


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
        self.logger.debug('Entering election loop')
        cf = ChannelFactory.get_instance()
        while True:
            if not self.__run:
                break
            self.__thread_event.clear()
            were_mb = self.is_master_message_broker()

            try:
                self.__master_broker = cf.determine_master_message_broker(value=self.__server_id,ttl=MasterElector.ELECTOR_TTL_IN_SECONDS)
            except Exception, ex:
                self.logger.error("Error determining master broker: %s" % ex)
                self.__thread_event.wait(MasterElector.ELECTOR_SLEEP_PERIOD_IN_SECONDS)
                continue

            self.logger.debug("The current master broker is: %s" % self.__master_broker)

            if self.is_master_message_broker():
                # We are the master broker... lets make sure that our ttl is updated
                try:
                    cf.refresh_master_message_broker(ttl=MasterElector.ELECTOR_TTL_IN_SECONDS)
                except Exception, ex:
                    self.logger.error("Unable to refresh the master broker: %s" % ex)

                # We are now and if we weren't before trigger the callback
                if not were_mb and self.elected_callback:
                    try:
                        self.elected_callback()
                        self.logger.debug("Elected callback complete.")
                    except Exception, ex:
                        self.logger.warn("Exception calling demote callback")
                        self.logger.exception(ex)
            else:
                # We aren't the master broker.  If we were before lets call the demote callback
                if were_mb and self.demoted_callback:
                    try:
                        self.demoted_callback()
                    except Exception, ex:
                        self.logger.warn("Exception calling demote callback")
                        self.logger.exception(ex)

            # Monitoring thread sleep
            self.__thread_event.wait(MasterElector.ELECTOR_SLEEP_PERIOD_IN_SECONDS)

        self.logger.debug('Exiting election loop')

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

