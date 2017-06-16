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
import os
import inspect

class TraceLogRecord(logging.LogRecord):
    """
    Our trace log record class for overriding call stack
    """

    def __init__(self, name, level, fn, lno, msg, args, exc_info, func):
        logging.LogRecord.__init__(
            self, name, level, fn, lno, msg, args, exc_info, func)

        self.pathname, self.lineno, self.func = self.__find_trace_caller()

        self.filename = os.path.basename(self.pathname)

    def __find_trace_caller(self):
        """
        Custom method for getting stack trace when using the trace method
        """

        f = inspect.currentframe()

        caller = f.f_back.f_back.f_back.f_back.f_back.f_back

        frameinfo = inspect.getframeinfo(caller)

        return frameinfo.filename, frameinfo.lineno, frameinfo.function

