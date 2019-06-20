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
from urb.messaging.message import Message
from urb.messaging.channel_factory import ChannelFactory
from urb.log.log_manager import LogManager

class RetryManager(object):
    """ Retry manager class. """

    GREENLET_SLEEP_PERIOD_IN_SECONDS = 0.001
    MANAGER_SLEEP_PERIOD_IN_SECONDS = 5
    INITIAL_RETRY_INTERVAL_IN_SECONDS = 60
    MAX_RETRY_COUNT = 5

    def __init__(self, channel, initial_retry_interval, max_retry_count):
        self.__manage = False
        self.logger = LogManager.get_instance().get_logger(
            self.__class__.__name__)
        self.__thread_event = gevent.event.Event()
        self.channel = channel
        retry_channel_name = channel.name + '.retry'
        cf = ChannelFactory.get_instance()
        self.retry_channel = cf.create_channel(retry_channel_name)
        self.initial_retry_interval = initial_retry_interval
        self.max_retry_count = max_retry_count

    def retry(self, message):
        """ Retry message. """
        try:
            retry_count = message.get('retry_count', 0)
            retry_interval = message.get('retry_interval', self.initial_retry_interval)
            if retry_count > 0:
                retry_interval *= 2
            retry_count += 1

            now = time.time()
            retry_timestamp = now + retry_interval
            message['retry_count'] = retry_count
            message['max_retry_count'] = self.max_retry_count
            message['retry_interval'] = retry_interval
            message['retry_timestamp'] = retry_timestamp
        
            self.logger.debug('Time now: %s' % (now))
            self.logger.debug('Will retry message in %s seconds, at time %s' % (retry_interval, retry_timestamp))
            self.retry_channel.write_with_timestamp(message.to_json(), 
                long(retry_timestamp))
        except Exception as ex:
            self.logger.error(
                'Could not retry message %s: %s' % (message, ex))

    def manage(self):
        """ Managment thread. """
        self.logger.debug('Entering retry channel management loop')
        while True:
            if not self.__manage:
                break
            self.__thread_event.clear()
        
            (name,message_list) = self.retry_channel.read_timestamp_range()
            self.logger.debug('Message list: %s', message_list)
            for message_string in message_list:
                try:
                    message = Message.from_json(message_string)
                    retry_count = message.get('retry_count', 0)
                    self.logger.debug('Retry count is %s for message %s' % (retry_count,message))
                    if retry_count > self.max_retry_count:
                        self.logger.warn('Max. retry count exceded for message %s' % message)
                        continue

                    self.channel.write(message.to_json())
                except Exception as ex:
                    self.logger.error(
                        'Error writing message (%s) to channel %s: %s' % (
                        message_string, self.channel.name, ex))

                # Must allow other greenlets to run.
                gevent.sleep(RetryManager.GREENLET_SLEEP_PERIOD_IN_SECONDS)

            # Monitoring thread sleep
            self.__thread_event.wait(RetryManager.MANAGER_SLEEP_PERIOD_IN_SECONDS)

        self.logger.debug('Exiting retry manager loop')

    def stop(self):
        """ Stop manager. """
        self.logger.info("Retry manager: stopping")
        self.__manage = False
        self.__thread_event.set()
        self.__manager_thread.join()
        self.logger.debug("Retry manager: after join")
        
    def start(self):
        """ Start manager. """
        self.__manage = True
        self.__manager_thread = gevent.spawn(self.manage)
        return self.__manager_thread
        
    def is_managing(self):
        """ Are we managing retries? """
        return self.__manage
        
# Testing
if __name__ == '__main__':
    print('Done')

