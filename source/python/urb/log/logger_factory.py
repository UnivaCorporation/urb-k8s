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


import re
import logging

from trace_logger import TraceLogger

class LoggerFactory(object):
    def __init__(self, logger_expressions=None):
        """ Constructor...take in a list of regular expressions
            to match loggers against """
        self.expressions = []
        self.forced_level = logging.CRITICAL
        self.logger = logging.getLogger()
        if logger_expressions is not None:
            self.parse_expressions(logger_expressions)

    def get_logger(self, name):
        """ Get a logger by name and set its level accordingly """
        logger = logging.getLogger(name)
        logger.setLevel(self.get_level(name))
        return logger

    def get_level(self, name):
        """ Search through the list of expressions and find the level
            that matches a specific name.  If there isn't a match fall
            through to the next in the heirarchy """
        level = logging.NOTSET
        # Iterate in reverse as the last is most significant
        for exp in reversed(self.expressions):
            pattern, level = exp
            # If we return non None its a match
            if not None == pattern.match(name):
                # If we are forcing to a less severe level than the one we
                # matched we must override the level
                if level >= self.forced_level:
                    level = self.forced_level
                break

        return level

    def force_level(self, level):
        """ Force all loggers to at least a specific level """
        self.forced_level = level
        self.logger.setLevel(level)
        #self.logger.\
        #    log(TraceLogger.TRACE, 'Forced all loggers to %s' % level)

    def parse_expressions(self, expressions):
        """ Parse a list of logger matching expressions of the form
            <regex>=<log-level>.  Place the compiled regex's and levels
            in the expressions attribute. """
        lines = expressions.split('\n')
        for line in lines:
            try:
                # Use the right split so we can have '='s in the regex
                regex, level = line.rsplit('=', 1)
                pattern = re.compile(regex)
                results = (pattern, logging.getLevelName(level.upper()))

                self.logger.log(
                    TraceLogger.TRACE,
                    'Appending %s:%s to logger level expressions' % (
                        results[0], results[1]))

                self.expressions.append(results)
            except Exception, ex:
                self.logger.\
                    error('Parser error in log configuration file: %s' % (
                        line))
                self.logger.exception(ex)
