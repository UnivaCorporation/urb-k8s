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

