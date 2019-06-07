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
from urb.log.log_manager import LogManager
from urb.messaging.channel_factory import ChannelFactory
from urb.messaging.service_shutdown_message import ServiceShutdownMessage

class URBServiceController:
    """ URB service controller class. """

    def __init__(self, service_monitor_channel):
        self.service_monitor_channel = service_monitor_channel
        self.logger = LogManager.get_instance().get_logger(
            self.__class__.__name__)

    def send_shutdown_message(self):
        try:
            cf = ChannelFactory.get_instance()
            channel = cf.create_channel(self.service_monitor_channel)
            payload = { 'timestamp' : time.time() }
            message = ServiceShutdownMessage(source_id='urb.service.controller', payload=payload)
            self.logger.debug(
                'Sending shutdown message to channel %s' % \
                self.service_monitor_channel)
            channel.write(message.to_json())
        except Exception as ex:
            self.logger.error(
                'Could not send shutdown message to channel %s (error: %s)' % \
                (self.service_monitor_channel, ex))
    
# Run controller.
def run():
    try:
        from gevent import monkey; monkey.patch_socket()
        controller = URBServiceController('urb.service.monitor')
        controller.send_shutdown_message()
    except KeyboardInterrupt as ex:
        pass
            
# Testing
if __name__ == '__main__':
    run()
 


