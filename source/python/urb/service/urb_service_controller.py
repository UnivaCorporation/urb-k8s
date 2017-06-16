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
        except Exception, ex:
            self.logger.error(
                'Could not send shutdown message to channel %s (error: %s)' % \
                (self.service_monitor_channel, ex))
    
# Run controller.
def run():
    try:
        from gevent import monkey; monkey.patch_socket()
        controller = URBServiceController('urb.service.monitor')
        controller.send_shutdown_message()
    except KeyboardInterrupt, ex:
        pass
            
# Testing
if __name__ == '__main__':
    run()
 


