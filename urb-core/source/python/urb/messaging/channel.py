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
import time
from urb.log.log_manager import LogManager

class Channel(object):
    """ Channel class. """

    MESSAGE_WAIT_PERIOD_IN_SECONDS = 1
    GREENLET_SLEEP_PERIOD_IN_SECONDS = 0.001

    def __init__(self, name, message_broker):
        self.name = name
        self.message_broker = message_broker
        self.read_callback = None
        self.write_callback = None
        self.__listen = False
        self.logger = LogManager.get_instance().get_logger(
            self.__class__.__name__)

    def register_read_callback(self, read_callback):
       """ Register read callback. """
       self.read_callback = read_callback

    def unregister_read_callback(self):
       """ Unregister read callback. """
       self.read_callback = None

    def register_write_callback(self, write_callback):
       """ Register write callback. """
       self.write_callback = write_callback

    def unregister_write_callback(self):
       """ Unregister write callback. """
       self.write_callback = None

    def clear(self):
        """ Clear channel. """
        self.message_broker.clear_queue(self.name)

    def get_size(self):
        """ Return size. """
        return self.message_broker.get_queue_size(self.name)

    def is_empty(self):
        """ Return True if queue is empty, False otherwise. """
        return self.message_broker.is_queue_empty(self.name)

    def write(self, message):
        """ Put message into the queue. """
        self.message_broker.push(self.name, message)
        if message is not None and self.write_callback is not None:
            gevent.spawn(self.write_callback, message)

    def write_with_timestamp(self, message, timestamp=None):
        """ Put message into the queue with a timestamp. """
        if timestamp is None:
            timestamp = long(time.time())
        self.message_broker.push_with_score(self.name, timestamp, message)

    def __read_callback_wrapper(self, message):
       """ Simple wrapper to make sure we mark the message as processed
       """
       try:
           self.read_callback(message)
           self.message_processed(message[1])
       except Exception, ex:
           self.logger.error("Read callback for channel %s threw exception %s" % (self.name, ex))

    def read_blocking(self, timeout=0):
        """ Remove and return message from the queue. 
            Block until message is available, or until timeout.
        """
        message = self.message_broker.pop_blocking(self.name, timeout=timeout)
        if message is not None and self.read_callback is not None:
            #self.read_callback(message)
            gevent.spawn(self.__read_callback_wrapper, message)
        return message

    def read(self):
        """ Remove and return message from the queue. 
            Do not block.
        """
        message = self.message_broker.pop(self.name)
        if message is not None:
            message_tuple = (self.name,message)
            if self.read_callback is not None:
                #self.read_callback(message)
                gevent.spawn(self.__read_callback_wrapper, message_tuple)
            return message_tuple
        return None

    def read_timestamp_range(self, max_timestamp=None):
        """ Pop messages the queue within timestamp range. """
        if max_timestamp is None:
            max_timestamp = long(time.time())
        message_list = self.message_broker.pop_score_range(self.name, 
            max_timestamp)
        return (self.name,message_list)

    def message_processed(self,m):
        """ This message has been processed and can be removed from our
            processing queue """
        self.message_broker.message_processed(self.name,m)

    def listen(self):
        """ Listen for messages. """
        self.logger.debug('Entering listen loop')
        self.__check_for_lost_messages = True
        while True:
            if not self.__listen:
                break
            if self.__check_for_lost_messages:
                self.message_broker.restore_lost_messages(self.name)
                self.__check_for_lost_messages = False
            msg = None
            t1 = time.time()
            try:
                msg = self.read_blocking(
                        timeout=Channel.MESSAGE_WAIT_PERIOD_IN_SECONDS)
            except Exception, ex:
                # Couldn't find a master... lets sleep our normal wait period so we don't
                # thrash
                self.logger.error("Unable to read message on %s: %s" % (self.name, ex))
                t2 = time.time()
                gevent.sleep(Channel.MESSAGE_WAIT_PERIOD_IN_SECONDS - (t2-t1))
            if msg is not None:
                self.logger.trace('Got message on %s: %s' % msg) # msg is tuple (name, msg) or None
            else:
                self.logger.trace('No messages received on %s' % self.name)
            # Must allow other greenlets to run.
            gevent.sleep(Channel.GREENLET_SLEEP_PERIOD_IN_SECONDS)
        self.logger.debug('Exiting listen loop')

    def stop_listener(self):
        """ Stop listener. """
        self.__listen = False
        
    def start_listener(self):
        """ Start listener. """
        self.__listen = True
        listener = gevent.spawn(self.listen)
        return listener
        
    def is_listening(self):
        """ Are we listening for messages? """
        return self.__listen
        
# Testing
if __name__ == '__main__':
    import time
    from redis_message_broker import RedisMessageBroker
    message_broker = RedisMessageBroker()
    channel_name = 'test_channel'
    channel = Channel(channel_name, message_broker)
    channel.clear()
    message = 'XYZ'
    channel.write(message)
    print 'Pushed: ', message
    print 'Q Size: ', channel.get_size()
    message = channel.read_blocking()
    print 'Popped: ', message
    print 'Q Size: ', channel.get_size()

    def read_callback(msg):
        print 'BEGIN READ CALLBACK', time.time()
        print 'READ: ', msg, time.time()
        print 'END READ CALLBACK', time.time()
    channel.register_read_callback(read_callback)

    def write_callback(msg):
        print 'BEGIN WRITE CALLBACK', time.time()
        print 'WRITE: ', msg
        print 'END WRITE CALLBACK', time.time()
    channel.register_write_callback(write_callback)

    message = 'XYZ'
    channel.write(message)
    print 'Pushed: ', message
    print 'Q Size: ', channel.get_size()
    message = channel.read_blocking()
    print 'Popped: ', message
    print 'Q Size: ', channel.get_size()

    print 'ENTER listener loop'
    listener = channel.start_listener()
    print 'Listener: ', listener
    for i in range (0, 10):
        message = 'This is message #%s' % i
        print 'Writing message: ', message
        channel.write(message)
        gevent.sleep(0.001)
    print 'SLEEPING...'
    time.sleep(10)
    print 'Stopping listener'
    channel.stop_listener()
    gevent.joinall([listener])
    
    print 'Done'

     
