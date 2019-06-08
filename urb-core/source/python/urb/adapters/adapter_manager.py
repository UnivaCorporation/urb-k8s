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


import sys
import os
from urb.config.config_manager import ConfigManager
from urb.log.log_manager import LogManager
from urb.exceptions.configuration_error import ConfigurationError

class AdapterManager(object):

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
        if AdapterManager.__instance is not None:
            return
        self.logger = LogManager.get_instance().get_logger(
            self.__class__.__name__)
        self.adapter_dict = {}
            
    def __create_adapter(self, interface_name, channel_name):
        """ Create adapter instance. """
        self.logger.debug('Creating adapter for interface: %s' % interface_name)
        adapter_option_name = '%s_adapter' % interface_name
        adapter_path_option_name = '%s_adapter_path' % interface_name
        cm = ConfigManager.get_instance()
        adapter_path = cm.get_config_option('AdapterManager', adapter_path_option_name)
        adapter_config = cm.get_config_option('AdapterManager', adapter_option_name)
        self.logger.debug('adapter_path=%s, adapter_config=%s' % (adapter_path, adapter_config))
        if adapter_config is None:
            raise ConfigurationError(
                'Adapter parameter %s missing from config file: %s' 
                % (adapter_option_name, cm.get_config_file()))
        dot_pos = adapter_config.find('.')
        if dot_pos == -1:
            raise ConfigurationError("Incorrect adapter format: should be in form <handlername>_adapter=adapter_module.AdapterClass(arg1, arg2, ...)")
        self.adapter_module = adapter_config[:dot_pos]
        self.adapter_constructor = adapter_config[dot_pos+1:]
        self.logger.trace('adapter_module=%s, adapter_constructor=%s' % (self.adapter_module, self.adapter_constructor))
        try:
            self.adapter_class = self.adapter_constructor.split('(')[0]
            self.logger.trace('adapter_class=%s' % self.adapter_class)
            if adapter_path is not None:
                if adapter_path[0] == ".":
                    self.logger.trace('adapter_path is relative')
                    # relative path
                    adapter_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), adapter_path)
                self.logger.trace('adapter_path=%s' % adapter_path)
                sys.path.append(adapter_path)
                self.logger.trace('Executing: from %s import %s' % (self.adapter_module, self.adapter_class))
                exec 'from %s import %s' % (self.adapter_module, self.adapter_class)
                exec 'adapter = %s' % self.adapter_constructor
            else:
                adapter_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../..", self.adapter_module)
                self.logger.trace('adapter_path=%s' % adapter_path)
                sys.path.append(adapter_path)
                self.logger.trace('Executing: from %s.%s import %s' % (self.adapter_module, self.adapter_module, self.adapter_class))
                exec 'from %s.%s import %s' % (self.adapter_module, self.adapter_module, self.adapter_class)
                exec 'adapter = %s' % self.adapter_constructor
        except Exception as ex:
            self.logger.error('AdapterManager configuration error: %s' % ex)
            raise ConfigurationError(exception=ex)

        return adapter

    def get_adapter(self, interface_name, channel_name):
        """ Get adapter. """
        adapter = self.adapter_dict.get(interface_name)
        if adapter is None:
            adapter = self.__create_adapter(interface_name, channel_name)
            adapter.set_channel_name(channel_name)
            self.adapter_dict[interface_name] = adapter
        return adapter

# Testing
if __name__ == '__main__':
    am = AdapterManager.get_instance()
    adapter = am.get_adapter('mesos')
    print adapter

