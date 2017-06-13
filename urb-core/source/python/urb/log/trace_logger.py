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


import logging
from trace_log_record import TraceLogRecord

class TraceLogger(logging.getLoggerClass()):
    # Use a level of 5...in logging module 0 = NOTSET and 10 = DEBUG
    TRACE = 5

    # Name to use when printing log level
    TRACE_NAME = 'TRACE'

    @classmethod
    def getLogLevel(cls, level_str):
        """ Return the int level that matches level_str if we know it """
        level = None
        if level_str == TraceLogger.TRACE_NAME:
            level = TraceLogger.TRACE
        return level

    @classmethod
    def register(cls):
        """ Register custom trace logger with the logging subsystem """

        # Register a new level / name mapping
        logging.addLevelName(TraceLogger.TRACE, TraceLogger.TRACE_NAME)

        # Override the default logging class for the python logger
        logging.setLoggerClass(TraceLogger)

    def trace(self, msg, *args, **kwargs):
        """ Trace call wrapping the logging.log method """
        if self.manager.disable >= TraceLogger.TRACE:
            return

        if TraceLogger.TRACE >= self.getEffectiveLevel():
            self.log(TraceLogger.TRACE, msg, *args, **kwargs)

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                   func=None, extra=None):
        """
        Custom makeRecord so call stack variables can be updated with
        proper values
        """

        if level == TraceLogger.TRACE:
            return TraceLogRecord(
                name, level, fn, lno, msg, args, exc_info, func)

        return logging.Logger.makeRecord(
            self, name, level, fn, lno, msg, args, exc_info, func)

