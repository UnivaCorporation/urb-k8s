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
import re
import logging
from urb.exceptions.configuration_error import ConfigurationError
from urb.config.config_manager import ConfigManager
from trace_logger import TraceLogger
from logger_factory import LoggerFactory

class LogManager(object): 
    """
    Singleton class for logging management.

    Usage:
        # Getting logger.
        from urb.utility.log_manager import LogManager
        lm = LogManager.get_instance()
        logger = lm.get_logger('MyClass')

        # The following are different logging methods.
        logger.info('This is an info message')
        logger.debug('This is a debug message')
        logger.trace('This is a trace message')
        logger.warning('This is a warning message')
        logger.error('This is an error message')
        logger.critical('This is a critical error message')

        # The logger.exception() method should be called from an exception
        # handler only.
        try:
            myObject.someMethod()
        except Exception as ex:
            logger.exception('A bad thing happened.')

        # These methods are used to set user/system logging levels.
        lm.set_console_log_level('info')
        lm.set_file_log_level('debug')

    Configuration:
        The log manager class is initialized via a configuration file
        that may have the following sections:
            ConsoleLogging      # Used for output on the screen
            FileLogging         # Used for logging into a file

        If any of the above sections is missing from the configuration file,
        the correspondign handler is not instantiated (except for the
        console handler that is configured using predefined defaults).

        Each section in the configuration file should have the following
        keys:
            handler     # Indicates which handler class to use
            level       # Indicates logging level
            format      # Indicates format for log messages
            datefmt     # Indicates date format used for log messages

        Given below is an example of a valid configuration file:

            [ConsoleLogging]
            handler=StreamLogHandler(sys.stdout,)
            level=info
            format=[%(levelname)s] %(message)s
            datefmt=%m/%d/%y %H:%M:%S

            [RemoteLogging]
            handler=SocketLogHandler('localhost', 10020)
            level=notset
            format=%(asctime)s,%(msecs)d [%(levelname)s]
                %(module)s:%(lineno)d %(user)s@%(host)s %(name)s
                (%(process)d): %(message)s
            datefmt=%m/%d/%y %H:%M:%S

            [FileLogging]
            handler=TimedRotatingFileLogHandler('/tmp/urb.log')
            level=debug
            format=%(asctime)s,%(msecs)d [%(levelname)s]
                %(module)s:%(lineno)d %(user)s@%(host)s %(name)s
                (%(process)d): %(message)s
            datefmt=%m/%d/%y %H:%M:%S
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
        """ Initialize log manager instance. """
        # Only initialize once.
        if LogManager.__instance is not None:
            return
        self.user_handler_list = []
        self.system_handler_list = []

        self.loggerFactory = None

        # Register custom trace logger
        TraceLogger.register()
        self.__configure_handlers()

    def __get_log_level(self, level_str):
        # Get Log Level based on a string representation
        level = logging.getLevelName(level_str)
        # Level should be an integer
        try:
            return int(level)
        except ValueError:
            raise ValueError(
                '"%s" is not valid log/debug level' % (level_str))

    def __configure_handlers(self):
        """ Configure all log handlers from the config file. """
        cm = ConfigManager.get_instance()

        # Config manager will return the requested setting, or
        # its own default values if the default value is not passed in.
        handler = 'stream_log_handler.StreamLogHandler(sys.stderr,)'
        level = cm.get_console_log_level(None)
        format_ = cm.get_log_record_format(None)
        datefmt = cm.get_log_date_format(None)

        defaults = {
            'level': cm.get_console_log_level(),
            'format': cm.get_log_record_format(),
            'datefmt': cm.get_log_date_format(),
            'handler': handler
        }

        console_handler = None
        if cm.get_console_log_level() != 'notset':
            console_handler = self.__configure_handler(
                'ConsoleLogging', defaults, handler, level,
                format_, datefmt)

        if console_handler is not None:
            self.user_handler_list.append(console_handler)

        # Local file logging (only turned on if it is in the config file).
        handler = None
        level = cm.get_file_log_level(None)

        defaults['level'] = cm.get_file_log_level()
        defaults['handler'] = handler

        # Parse all of the file loggers present in the config file
        config_sections = cm.get_config_sections()
        for config_section in config_sections:
            if config_section.startswith('FileLogging'):
                fileHandler = self.__configure_handler(
                    config_section, defaults, handler, level,
                    format_, datefmt)

                if fileHandler is not None:
                    self.system_handler_list.append(fileHandler)

        # Remote logging (only turned on if it is in the config file).
        remoteHandler = self.__configure_handler(
            'RemoteLogging', defaults, handler, level, format_,
            datefmt)

        if remoteHandler is not None:
            self.system_handler_list.append(remoteHandler)

        # Add handlers to the root logger.  Use logging class here
        # to make sure we can have a logger when we parse the
        # logger expressions
        root_logger = logging.getLogger('')

        for handler in self.user_handler_list + self.system_handler_list:
            root_logger.addHandler(handler)

        # Now get a logger factory based on our current config
        self.logger_factory = self.__create_logger_factory()

    def __create_logger_factory(self):
        cm = ConfigManager.get_instance()
        root_log_level = cm.get_config_option('LoggerLevels', 'root', 'error')
        root_level_int = logging.getLevelName(root_log_level.upper())
        root_logger = logging.getLogger('')
        root_logger.root.setLevel(root_level_int)
        root_logger.debug('Set root logger to %s' % root_level_int)
        expressions = cm.get_config_option('LoggerLevels', 'expressions')
        return LoggerFactory(expressions)

    def __configure_handler(self, config_section, defaults,
                            handler, level, format_, datefmt):
        """ Configure specified handler with a given defaults. """
        cm = ConfigManager.get_instance()
        cm.set_config_defaults(defaults)
        handler_option = cm.get_config_option(config_section, 
                'handler', handler)

        # If handler_option is empty, handler cannot be instantiated.
        _handler = None
        if handler_option is not None:
            # Handler argument format: my_module.MyHandler(arg1, arg2, ...)
            # Module will be in lowercase letters, but the class
            # should be capitalized.
            handler_name = re.sub(r'\(.*', '', handler_option)
            module_name = handler_name.split('.')[0]
            try:
                exec('from urb.log import %s' % (module_name))
                exec('_handler = %s' % (handler_option))
            except IOError as ex:
                _errno = ex.errno
                import errno

                # If the exception raised is an I/O permissions error,
                # ignore it and disable this log handler.  This allows
                # non-root users to use the (system-wide) default log
                # configuration
                if _errno != errno.EACCES:
                    raise
                _handler = None
            except Exception as ex:
                raise ConfigurationError(exception=ex)

        # Only request setting from the config file if it was
        # not set via environment variable, or programmatically.
        if _handler is not None:
            try:
                _level = level
                if _level is None:
                    _level = cm.get_config_option(
                        config_section, 'level', defaults['level'])
                intLevel = self.__get_log_level(_level.upper())
                _handler.setLevel(intLevel)

                _format = format_
                if _format is None:
                    _format = cm.get_config_option(
                        config_section, 'format', defaults['format'])

                _datefmt = datefmt
                if _datefmt is None:
                    _datefmt = cm.get_config_option(
                        config_section, 'datefmt', defaults['datefmt'])

                _handler.setFormatter(logging.Formatter(_format, _datefmt))
            except Exception as ex:
                raise ConfigurationError(exception=ex)

            # Look to see if there is a filter to apply to the handler
            filter_ = None

            try:
                filter_ = cm.get_config_option(config_section, 'filter')
            except Exception as ex:
                pass

            if filter_:
                _handler.addFilter(logging.Filter(filter_))

        return _handler

    def get_logger(self, name):
        """ Get logger with a given name. """
        return self.logger_factory.get_logger(name)

    def set_console_log_level(self, level):
        """ Set user log level. """
        try:
            # We need to override the logger levels and the handler
            intLevel = self.__get_log_level(level.upper())
            for handler in self.user_handler_list:
                handler.setLevel(intLevel)
            self.logger_factory.force_level(intLevel)
        except Exception as ex:
            raise ConfigurationError(exception=ex)

    def set_file_log_level(self, level):
        """ Set system log level. """
        try:
            # We need to override the logger levels and the handler
            intLevel = self.__get_log_level(level.upper())
            for handler in self.system_handler_list:
                handler.setLevel(intLevel)
            self.logger_factory.force_level(intLevel)
        except Exception as ex:
            raise ConfigurationError(exception=ex)

# Testing.
if __name__ == '__main__':
    lm = LogManager.get_instance()
    lm.set_console_log_level('trace')
    lm.set_file_log_level('trace')
    logger1 = lm.get_logger('log1')
    logger2 = lm.get_logger('log2')
    logger1.debug('Hello there, debug')
    logger2.trace('Hello there, trace')
