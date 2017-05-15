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


import json
import uuid

from urb.log.log_manager import LogManager
from urb.messaging.channel_factory import ChannelFactory
from urb.messaging.message import Message
from urb.exceptions.invalid_command import InvalidCommand
from urb.exceptions.urb_exception import URBException

class MessageHandler:
  
    def __init__(self, channel_name=None):
        self.name = self.__class__.__name__
        self.logger = LogManager.get_instance().get_logger(self.name)
        cf = ChannelFactory.get_instance()
        self.channel = cf.create_channel(channel_name)
        self.channel.register_read_callback(self.handle)

    def listen(self):
        return self.channel.start_listener()

    def get_target_preprocessor(self, target):
        return None

    def get_target_executor(self, target):
        return None

    def get_target_postprocessor(self, target):
        return None

    def get_response_channel_name(self, request):
        response_channel_name = request.get('reply_to')
        if response_channel_name is None:
            source_id = request.get('source_id')
            if source_id is None:
                return None
            # base1, base2, id, [sub-channel]
            parts = source_id.split('.')
            if len(parts) == 3:
                response_channel_name = 'urb.endpoint.' + parts[2] + '.notify'
            else:
                # Use as is...
                response_channel_name = source_id
        self.logger.debug('Determined response channel name: %s' \
            % response_channel_name)
        return response_channel_name

    def send_response(self, request, response):
        if response is None:
            return
        channel_name = "Unset"
        try:
            channel_name = self.get_response_channel_name(request)
            if channel_name is None:
                return
            cf = ChannelFactory.get_instance()
            channel = cf.create_channel(channel_name)
            channel.write(response.to_json())
            self.logger.trace('Wrote response to %s: %s' % (channel_name, 
                response.to_json()))
        except Exception, ex:
            self.logger.error(
                'Could not send response to channel %s (error: %s)' % \
                (channel_name, ex))
    
    def handle(self, message):
        try:
            # Convert message from json.
            request = Message.from_json(message[1])
            response = None

            # Check target.
            self.logger.trace('Got request: %s' % request)
            target = request.get('target')
            if target is None:
                self.logger.error('Wrong target: %s' % target)

            # Assign message id.
            request['message_id'] = str(uuid.uuid1())

            # Preprocess request.
            try:
                target_preprocessor = self.get_target_preprocessor(target)
                if target_preprocessor is not None:
                    self.logger.debug('Preprocessing target %s using preprocessor %s' % (target, target_preprocessor)) 
                    target_preprocessor(request)
            except URBException, ex:
                self.logger.error(ex)
            except Exception, ex:
                errMsg = 'Cannot preprocess target %s: %s' % (target,ex)
                self.logger.error(errMsg)
                self.logger.exception(ex)
            
            # Process request.
            target_executor = self.get_target_executor(target)
            if target_executor is None:
                errMsg = 'Unsupported target: %s' % target
                self.logger.error(errMsg)
                response = Message(payload=InvalidCommand(errMsg).to_dict())
            else:
                try:
                    self.logger.debug('Processing request with: %s' % target_executor) 
                    response = target_executor(request)
                    self.logger.trace('Response message: %s' % response) 
                except URBException, ex:
                    response = Message(payload=ex.to_dict())
                    self.logger.error(ex)
                except Exception, ex:
                    response = Message(payload={'error' : '%s' % ex})
                    errMsg = 'Cannot handle message: %s' % ex
                    self.logger.error(errMsg)
                    self.logger.exception(ex)
            self.send_response(request, response)

            # Postprocess request.
            try:
                target_postprocessor = self.get_target_postprocessor(target)
                if target_postprocessor is not None:
                    self.logger.debug('Postprocessing target %s using postprocessor %s' % (target, target_postprocessor)) 
                    target_postprocessor(request)
            except URBException, ex:
                self.logger.error(ex)
            except Exception, ex:
                errMsg = 'Cannot postprocess target %s: %s' % (target,ex)
                self.logger.error(errMsg)
                self.logger.exception(ex)
            
        except Exception, ex:
            self.logger.error('Wrong json format for message: %s' % message[1])
            self.logger.exception(ex)

    def elected_master_callback(self):
        self.logger.debug('Master elected callback')
        self.channel.start_listener()

    def demoted_callback(self):
        self.logger.debug('Demoted callback')
        self.channel.stop_listener()

    def register_shutdown_callback(self, shutdown_callback):
        pass
