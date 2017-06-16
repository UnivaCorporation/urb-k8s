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

