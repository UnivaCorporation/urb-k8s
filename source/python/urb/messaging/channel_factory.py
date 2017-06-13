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


from urb.config.config_manager import ConfigManager
from urb.constants import liburb
from urb.log.log_manager import LogManager
from urb.exceptions.configuration_error import ConfigurationError
from channel import Channel

class ChannelFactory(object):

    BASE_CHANNEL_NAME = 'urb.endpoint'
    MASTER_BROKER_NAME = 'urb.master'

    # Singleton.
    __instance = None

    def __new__(cls, *args, **kwargs):
        # Allow subclasses to create their own instances.
        if cls.__instance is None or cls != type(cls.__instance):
            instance = object.__new__(cls, *args, **kwargs)
            instance.__init__()
            cls.__instance = instance
        return cls.__instance

    @classmethod
    def get_instance(cls, *args, **kwargs):
        return cls.__new__(cls, *args, **kwargs)

    def __init__(self):
        """ Initialize factory instance. """
        # Only initialize once.
        if ChannelFactory.__instance is not None:
            return
        cm = ConfigManager.get_instance()
        message_broker = cm.get_config_option(
            'ChannelFactory', 'message_broker')
        self.logger = LogManager.get_instance().get_logger(
            self.__class__.__name__)
        self.logger.debug('Using message broker: %s' % message_broker)
        if message_broker is None:
            raise ConfigurationError(
                'Message broker parameter missing from config file: %s' 
                % cm.get_config_file())
        dot_pos = message_broker.find('.')
        self.message_broker_module = message_broker[0:dot_pos]
        self.message_broker_constructor = message_broker[dot_pos+1:]
        self.message_broker_class = \
            self.message_broker_constructor.split('(')[0]
        self.message_broker = self.__get_message_broker()
            
    def __get_message_broker(self):
        """ Create instance of message broker class. """
        exec 'from %s import %s' % (self.message_broker_module,
            self.message_broker_class)
        exec 'mb = %s' % self.message_broker_constructor
        return mb

    def create_channel(self, name):
        """ Create new channel. """
        return Channel(name, self.message_broker)

    def destroy_channel(self, name):
        """ Destroy channel. """
        self.message_broker.delete_queue(name)

    def get_message_broker_connection_port(self):
        """ Return port used for message broker connection. """
        return self.message_broker.get_connection_port()

    def get_message_broker_connection_host(self):
        """ Return host used for message broker connection. """
        return self.message_broker.get_connection_host()

    def get_message_broker_connection_url(self):
        """ Return Liburb compatible URL to the message broker """
        url = "%s://%s:%s" % (liburb.LIBURB_URL_SCHEME,
                              self.get_message_broker_connection_host(),
                              self.get_message_broker_connection_port())
        return url

    def get_unique_channel_name(self):
        """ Return unique channel id. """
        return self.message_broker.get_unique_channel_name(
            ChannelFactory.BASE_CHANNEL_NAME)

    def get_channel_names(self, name_pattern):
        """ Return list of channel names. """
        return self.message_broker.get_channel_names(name_pattern)

    def determine_master_message_broker(self, value=None, ttl=60):
        return self.message_broker.determine_master_message_broker(ChannelFactory.MASTER_BROKER_NAME,value,ttl)

    def refresh_master_message_broker(self, value=None, ttl=60):
        return self.message_broker.refresh_master_message_broker(ChannelFactory.MASTER_BROKER_NAME,ttl)

# Testing
if __name__ == '__main__':
    cf = ChannelFactory.get_instance()
    channel = cf.create_channel('test_channel')
    print 'Port: ', cf.get_message_broker_connection_port()
    print 'Host: ', cf.get_message_broker_connection_host()
    print channel
    msg = 'Test'
    channel.write(msg)
    msg2 = channel.read()

    print 'Write: ', msg
    print 'Read: ', msg2

    print cf.get_unique_channel_name()

