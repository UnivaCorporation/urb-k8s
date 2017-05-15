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
from urb.utility.channel_tracker import ChannelTracker
from urb.log.log_manager import LogManager

class ChannelMonitor(object):
    """ Channel monitor class. """

    GREENLET_SLEEP_PERIOD_IN_SECONDS = 0.001
    MONITOR_SLEEP_PERIOD_IN_SECONDS = 15
    CHANNEL_INITIAL_TTL_IN_SECONDS = 60
    CHANNEL_TTL_GRACE_PERIOD_IN_SECONDS = 180

    def __init__(self, channel_validate_callback, channel_delete_callback):
        self.__monitor = False
        self.logger = LogManager.get_instance().get_logger(
            self.__class__.__name__)
        self.channel_delete_callback = channel_delete_callback
        self.channel_validate_callback = channel_validate_callback
        self.__thread_event = gevent.event.Event()

    def start_channel_monitoring(self, channel_id, framework_id=None, slave_id=None, time_to_live=None):
        self.logger.debug('Start monitoring channel id %s for framework id %s' % (channel_id, framework_id))
        now = time.time()
        if time_to_live is None or time_to_live < now:
            time_to_live = now + ChannelMonitor.CHANNEL_INITIAL_TTL_IN_SECONDS 
            self.logger.debug('Setting ttl to %s' % (time_to_live))
        channel_info = {
            'framework_id' : framework_id, 
            'slave_id' : slave_id, 
            'time_to_live' : time_to_live
        }
        ChannelTracker.get_instance().add(channel_id, channel_info)

    def stop_channel_monitoring(self, channel_id):
        self.logger.debug('Stop monitoring channel id %s' % (
            channel_id))
        channel_info = ChannelTracker.get_instance().get(channel_id)
        if channel_info is not None:
            self.__remove_channel_from_tracker(channel_id, channel_info)

    def __remove_channel_from_tracker(self, channel_id, channel_info):
        self.logger.debug('Removing channel id %s from tracker' % channel_id)
        ChannelTracker.get_instance().remove(channel_id)
        try:
            self.channel_delete_callback(channel_id, channel_info)
        except Exception, ex:
            self.logger.error(
                'Error invoking delete callback for channel id %s: %s' % (
                        channel_id, ex))

    def monitor(self):
        """ Monitoring thread. """
        self.logger.debug('Entering channel monitoring loop')
        channel_tracker = ChannelTracker.get_instance()
        while True:
            if not self.__monitor:
                break
            self.__thread_event.clear()
            channel_id_list = channel_tracker.keys()
            for channel_id in channel_id_list:
                channel_info = None
                try:
                    channel_info = channel_tracker.get(channel_id)
                    if channel_info is None:
                        self.logger.warn('No channel info for id %s' % channel_id)
                        channel_tracker.remove(channel_id)
                        continue
                    now = time.time()
                    ttl = channel_info.get('time_to_live', 0)
                    framework_id = channel_info.get('framework_id')
                    slave_id = channel_info.get('slave_id')
                    executor_id = channel_info.get('executor_id')
                    if now > ttl + ChannelMonitor.CHANNEL_TTL_GRACE_PERIOD_IN_SECONDS:
                        self.logger.debug('Channel id %s has expired ttl=%s, now=%s' % 
                            (channel_id, ttl, now))
                        # Remove channel from tracker
                        self.__remove_channel_from_tracker(channel_id, channel_info)
                        continue
                    elif now > ttl:
                        self.logger.debug('Channel id %s is past ttl=%s, now=%s' % 
                            (channel_id, ttl, now))
                    else:
                        self.logger.debug('Channel id %s is within ttl=%s, now=%s' % 
                            (channel_id, ttl, now))
                    try:
                        self.channel_validate_callback(channel_id, channel_info)
                    except Exception, ex:
                        self.logger.error(
                            'Error invoking callback validate for channel id %s: %s' % (
                                    channel_id, ex))

                except Exception, ex:
                    self.logger.warn(
                        'Error removing for channel id %s: %s' % (
                        channel_id, ex))

                # Must allow other greenlets to run.
                gevent.sleep(ChannelMonitor.GREENLET_SLEEP_PERIOD_IN_SECONDS)

            # Monitoring thread sleep
            self.__thread_event.wait(ChannelMonitor.MONITOR_SLEEP_PERIOD_IN_SECONDS)

        self.logger.debug('Exiting channel monitoring loop')

    def stop(self):
        """ Stop monitor. """
        self.__monitor = False
        self.__thread_event.set()
        self.__monitor_thread.join()
        
    def start(self):
        """ Start monitor. """
        self.__monitor = True
        self.__monitor_thread = gevent.spawn(self.monitor)
        return self.__monitor_thread
        
    def is_monitoring(self):
        """ Are we monitoring channels? """
        return self.__monitor
        
# Testing
if __name__ == '__main__':
    print 'Done'

