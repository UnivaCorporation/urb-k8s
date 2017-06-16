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
        if adapter_config is None:
            raise ConfigurationError(
                'Adapter parameter %s missing from config file: %s' 
                % (adapter_option_name, cm.get_config_file()))
        self.adapter_module = adapter_config.split('.')[0]
        self.adapter_constructor = adapter_config.split('.')[1]
        try:
            self.adapter_class = self.adapter_constructor.split('(')[0]
            if adapter_path is not None:
                if adapter_path[0] == ".":
                    # relative path
                    adapter_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), adapter_path)
            else:
                adapter_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../..", self.adapter_module)
            sys.path.append(adapter_path)

#            exec 'from %s import %s' % (self.adapter_module, self.adapter_class)
            exec 'from %s.%s import %s' % (self.adapter_module, self.adapter_module, self.adapter_class)
            exec 'adapter = %s' % self.adapter_constructor
        except Exception, ex:
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

