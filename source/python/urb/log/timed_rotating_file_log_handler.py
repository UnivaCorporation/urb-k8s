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


from logging.handlers import TimedRotatingFileHandler

from urb.config import config_manager

class TimedRotatingFileLogHandler(TimedRotatingFileHandler):
    """
    Class that enables logging into files. Log files can be rotated
    according to specified schedule.

    Usage:
        fh = TimedRotatingFileHandler('/tmp/urb.log')
    """

    def __init__(self, filename, when='D', interval=1, backupCount=0,
                 encoding=None):
        """ Initialize log handler. """
        TimedRotatingFileHandler.__init__(
            self, filename, when, interval, backupCount, encoding)
        cm = config_manager.ConfigManager.get_instance()
        self.user = cm.get_user()
        self.host = cm.get_host()

    def emit(self, record):
        """ Emit the log record. """
        record.__dict__['user'] = self.user
        record.__dict__['host'] = self.host
        return TimedRotatingFileHandler.emit(self, record)
