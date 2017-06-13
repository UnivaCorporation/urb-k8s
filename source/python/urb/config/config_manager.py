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


import os
import pwd
import socket
import subprocess

import UserDict
import ConfigParser

# Defaults.
DEFAULT_URB_ROOT = '/opt/urb'
DEFAULT_URB_ETC = os.path.join(DEFAULT_URB_ROOT, 'etc')
DEFAULT_URB_BIN = os.path.join(DEFAULT_URB_ROOT, 'bin')
DEFAULT_URB_LOG_FILE = '/var/log/urb'
DEFAULT_URB_CONFIG_FILE = os.path.join(
    DEFAULT_URB_ETC, 'urb.conf')
DEFAULT_URB_CONSOLE_LOG_LEVEL = 'info'
DEFAULT_URB_FILE_LOG_LEVEL = 'debug'
DEFAULT_URB_LOG_RECORD_FORMAT = \
    ('%(asctime)s,%(msecs)d [%(levelname)s] %(module)s:%(lineno)d'
     ' %(user)s@%(host)s %(name)s (%(process)d): %(message)s')
DEFAULT_URB_LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


class ConfigManager(UserDict.UserDict, object):
    """
    Singleton class used for keeping system configuration data. The class
    initializes its data using predefined defaults, or from the following
    environment variables:
        URB_ROOT
        URB_CONFIG_FILE
        URB_LOG_FILE
        URB_CONSOLE_LOG_LEVEL
        URB_FILE_LOG_LEVEL
        URB_LOG_RECORD_FORMAT
        URB_LOG_DATE_FORMAT

    Usage:
        from usb.config import configManager
        cm = configManager.ConfigManager()
        cm.set_console_log_level('info')
        level = cm.get_console_log_level()
        cm['myKey'] = 'myValue'
        value = cm.get('myKey')
    """

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
        """ Initialize configuration data. """
        # Only initialize once.
        if ConfigManager.__instance is not None:
            return
        UserDict.UserDict.__init__(self)
        self.config_parser = None
        self['defaultRoot'] = DEFAULT_URB_ROOT
        self['defaultConfigFile'] = DEFAULT_URB_CONFIG_FILE
        self['defaultLogFile'] = DEFAULT_URB_LOG_FILE
        self['defaultConsoleLogLevel'] = DEFAULT_URB_CONSOLE_LOG_LEVEL
        self['defaultFileLogLevel'] = DEFAULT_URB_FILE_LOG_LEVEL
        self['defaultLogRecordFormat'] = DEFAULT_URB_LOG_RECORD_FORMAT
        self['defaultLogDateFormat'] = DEFAULT_URB_LOG_DATE_FORMAT

        # Settings that might come from environment variables.
        self.__set_from_env_variable('root', 'URB_ROOT')
        self.__set_from_env_variable('logFile', 'URB_LOG_FILE')
        self.__set_from_env_variable(
            'configFile', 'URB_CONFIG_FILE')
        self.__set_from_env_variable(
            'consoleLogLevel', 'URB_CONSOLE_LOG_LEVEL')
        self.__set_from_env_variable('fileLogLevel', 'URB_FILE_LOG_LEVEL')
        self.__set_from_env_variable(
            'logRecordFormat', 'URB_LOG_RECORD_FORMAT')
        self.__set_from_env_variable(
            'logDateFormat', 'URB_LOG_DATE_FORMAT')

        # Variables affected by URB_ROOT
        self['binDir'] = os.path.join(self.get_root(), 'bin')
        self['etcDir'] = os.path.join(self.get_root(), 'etc')

        # System info.
        self['host'] = socket.getfqdn()
        self['user'] = pwd.getpwuid(os.getuid())[0]
        #print os.environ["URB_CONFIG_FILE"]
        print self.get_config_file()

    # This function will ignore errors if environment variable is not set.
    def __set_from_env_variable(self, key, env_var):
        """
        Set value for the specified key from a given environment variable.
        This functions ignores errors for env. variables that are not set.
        """
        try:
            self[key] = os.environ[env_var]
        except:
            pass

    # This function will ignore errors if variable file is not present.
    def __set_from_var_file(self, key, var_file):
        """
        Set value for the specified key from a given file. The first line
        in the file is variable value.
        This functions ignores errors.
        """

        if os.path.exists(var_file):
            with open(var_file) as v:
                self[key] = v.readline().lstrip().rstrip()

    def __get_key_value(self, key, default='__internal__'):
        """
        Get value for a given key.
        Keys will be of the form 'logFile', and the default keys have
        the form 'defaultLogFile'.
        """
        default_key = "default" + key[0].upper() + key[1:]
        default_value = self.get(default_key, None)
        if default != '__internal__':
            default_value = default
        return self.get(key, default_value)

    def clear_config_parser(self):
        """ Clear config parser. """
        self.config_parser = None

    def get_config_parser(self, defaults={}):
        """ Return config parser, or none if config file cannot be found. """
        if self.config_parser is None:
            config_file = self.get_config_file()
            self.config_parser = ConfigParser.ConfigParser(defaults)
            if os.path.exists(config_file):
                self.config_parser.read(config_file)
        if self.config_parser is not None:
            self.config_parser.defaults = defaults
        return self.config_parser

    def get_host(self):
        """ Get machine hostname. """
        return self['host']

    def get_user(self):
        """ Get user. """
        return self['user']

    def set_root(self, root):
        """ Set root. """
        self['root'] = root

    def get_root(self, default='__internal__'):
        """
        Get root. If the root has not been set, the function
        will return the specified default value. If the default value is
        not specified, internal (predefined) default will be returned.
        """
        return self.__get_key_value('root', default)

    def get_bin_dir(self, default='__internal__'):
        return self.__get_key_value('binDir', default)

    def get_etc_dir(self, default='__internal__'):
        return self.__get_key_value('etcDir', default)

    def set_config_file(self, config_file):
        """ Set config file. """
        self['configFile'] = config_file
        self.config_parser = None

    def get_config_file(self, default='__internal__'):
        """
        Get configuration file. If the configuration file has not
        been set, the function will return the specified default value.
        If the default value is not specified, internal (predefined)
        default will be returned.
        """
        return self.__get_key_value('configFile', default)

    def set_log_file(self, log_file):
        """ Set log file. """
        self['logFile'] = log_file

    def get_log_file(self, default='__internal__'):
        """
        Get log file. If the log file has not been set, the function
        will return the specified default value. If the default value is
        not specified, internal (predefined) default will be returned.
        """
        return self.__get_key_value('logFile', default)

    def set_console_log_level(self, level):
        """ Set user log level. """
        self['consoleLogLevel'] = level

    def get_console_log_level(self, default='__internal__'):
        """
        Get user log level. If the user log level has not
        been set, the function will return the specified default value.
        If the default value is not specified, internal (predefined)
        default will be returned.
        """
        return self.__get_key_value('consoleLogLevel', default)

    def set_file_log_level(self, level):
        """ Set system log level. """
        self['fileLogLevel'] = level

    def get_file_log_level(self, default='__internal__'):
        """
        Get system log level. If the system log level has not
        been set, the function will return the specified default value.
        If the default value is not specified, internal (predefined)
        default will be returned.
        """
        return self.__get_key_value('fileLogLevel', default)

    def set_log_record_format(self, format_):
        """ Set log record format. """
        self['logRecordFormat'] = format_

    def get_log_record_format(self, default='__internal__'):
        """
        Get log record format. If the log record format has not
        been set, the function will return the specified default value.
        If the default value is not specified, internal (predefined)
        default will be returned.
        """
        return self.__get_key_value('logRecordFormat', default)

    def get_log_date_format(self, default='__internal__'):
        """
        Get log date (timestamp) format. If the log date format has not
        been set, the function will return the specified default value.
        If the default value is not specified, internal (predefined)
        default will be returned.
        """
        return self.__get_key_value('logDateFormat', default)

    def set_config_defaults(self, defaults={}):
        """ Set configuration defaults. """
        config_parser = self.get_config_parser()
        if config_parser is not None:
            config_parser.defaults = defaults

    def get_config_option(self, config_section, key, default_value=None):
        """ Get specified option from the configuration file. """
        config_parser = self.get_config_parser()
        if self.has_config_section(config_section):
            try:
                return config_parser.get(config_section, key, True)
            except ConfigParser.NoOptionError, ex:
                # ok, return default
                pass
        return default_value

    def get_config_sections(self):
        """ Return a list of the sections from the config file """
        config_parser = self.get_config_parser()
        if config_parser is not None:
            return config_parser.sections()
        return []

    def has_config_section(self, name):
        """ Return true if parser has config section """
        config_sections = self.get_config_sections()
        if name in config_sections:
            return True
        return False

    def get_config_items(self, config_section):
        """ Get available (key,value) pairs from the configuration file. """
        config_parser = self.get_config_parser()
        if config_parser is not None and \
                config_parser.has_section(config_section):
            return config_parser.items(config_section)
        else:
            return []

# Testing
if __name__ == '__main__':
    cm1 = ConfigManager.get_instance()
    print 'CONFIG_FILE: ', cm1.get_config_file()
    cm1.set_config_file('/tmp/xyz')
    print 'CONFIG_FILE: ', cm1.get_config_file()
    cm2 = ConfigManager()
    print 'cm1 = cm2:', cm1 == cm2
    print 'ROOT: ', cm1.get_root()
    print 'CONFIG_FILE: ', cm1.get_config_file()
    print 'CONFIG FILE SECTIONS: ', cm1.get_config_sections()
