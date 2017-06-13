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


from logging import StreamHandler
from urb.config import config_manager

class StreamLogHandler(StreamHandler):
    """
    Class that enables logging into a stream. It can be used for logging
    into standard output or error.

    Usage:
        sh = StreamLogHandler(sys.stdout,)
    """

    def __init__(self, *args):
        """ Initialize log handler. """
        StreamHandler.__init__(self, *args)
        cm = config_manager.ConfigManager.get_instance()
        self.user = cm.get_user()
        self.host = cm.get_host()

    def emit(self, record):
        """ Emit the log record. """
        record.__dict__['user'] = self.user
        record.__dict__['host'] = self.host
        return StreamHandler.emit(self, record)

