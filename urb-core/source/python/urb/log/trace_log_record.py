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

