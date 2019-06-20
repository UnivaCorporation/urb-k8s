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


import time
from urb.messaging.message_handler import MessageHandler
from urb.messaging.message import Message
from urb.messaging.heartbeat_message import HeartbeatMessage
from urb.messaging.service_shutdown_message import ServiceShutdownMessage
from urb.exceptions.urb_exception import URBException
from urb.utility.channel_tracker import ChannelTracker
from urb.service.channel_monitor import ChannelMonitor

class ServiceMonitorHandler(MessageHandler):

    SHUTDOWN_MESSAGE_EXPIRATION_PERIOD_IN_SECONDS = 10

    def __init__(self, channel_name):
        MessageHandler.__init__(self, channel_name)

    def get_target_executor(self, target):
        supported_target_executor = {
            'PingMessage' : self.ping,
            'HeartbeatMessage' : self.heartbeat,
            'ServiceShutdownMessage' : self.shutdown,
        }
        return supported_target_executor.get(target)

    def ping(self, request=None):
        self.logger.debug("ping: request=%s" % request)
        timestamp = time.strftime('%Y/%m/%d %H:%M:%S')
        payload = { 'ack' : 'URB Service is alive @ %s' % timestamp }
        return None, Message(payload=payload)

    def heartbeat(self, request):
        """ Heartbeat message should have the following format:
            channel_info : {
                'channel_id' : <notify channel id>,
                'framework_id' : <framework id>,
                'endpoint_type' : 'framework' | 'executor' | 'executor_runner'
                'slave_id' : [<slave id>], # optional
                'time_to_live' : [<time to live>] # optional
            }
        """
        self.logger.debug('Heartbeat message: %s' % request)
        payload = request.get('payload')
        if payload is None:
            raise URBException('Ignoring invalid heartbeat request: payload missing')

        channel_info = payload.get('channel_info')
        if channel_info is None:
            raise URBException('Ignoring invalid heartbeat request: channel_info missing')

        channel_id = channel_info.get('channel_id')
        if channel_id is None:
            raise URBException('Ignoring invalid heartbeat request: channel_id missing')

        endpoint_type = channel_info.get('endpoint_type')
        if endpoint_type is None:
            raise URBException('Ignoring invalid heartbeat request: endpoint_type missing')

        time_to_live = channel_info.get('time_to_live', time.time() + ChannelMonitor.CHANNEL_INITIAL_TTL_IN_SECONDS)
        channel_info['time_to_live'] = time_to_live

        self.logger.debug('Updating channel info for %s, ttl=%s' % (channel_id, time_to_live))
        ChannelTracker.get_instance().add(channel_id, channel_info)

        return None, None

    def register_shutdown_callback(self, shutdown_callback):
        self.shutdown_callback = shutdown_callback
        
    def shutdown(self, request):
        self.logger.debug('Received shutdown message')
        payload = request.get('payload')
        timestamp = payload.get('timestamp')
        now = time.time()
        if timestamp is None:
            self.logger.debug('Ignoring shutdown message, no timestamp')
        elif now > timestamp + ServiceMonitorHandler.SHUTDOWN_MESSAGE_EXPIRATION_PERIOD_IN_SECONDS:
            self.logger.debug('Ignoring expired shutdown message (timestamp: %s, now: %s)' % (timestamp, now))
        else: 
            self.logger.debug('Shutdown message is valid')
            self.shutdown_callback(request)
        return None, None

# Testing
if __name__ == '__main__':
    handler = ServiceMonitorHandler('x.y.z')
    print(handler.ping())

