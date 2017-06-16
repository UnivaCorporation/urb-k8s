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


import exceptions
import json

from urb.constants import urb_status

class URBException(exceptions.Exception):
    """
    Base URB exception class.

    Usage:
        URBException(errorMessage, errorCode)
        URBException(args=errorMessage)
        URBException(exception=exceptionObject)
    """

    def __init__(self, error='', code=urb_status.URB_ERROR,
                 **kwargs):
        args = error
        if args == "":
            args = kwargs.get('args', "")
        ex = kwargs.get('exception', None)
        if ex is not None and isinstance(ex, exceptions.Exception):
            exArgs = "%s" % (ex)
            if args == "":
                args = exArgs
            else:
                args = "%s (%s)" % (args, exArgs)
        exceptions.Exception.__init__(self, args)
        self.code = code

    #def __str__(self):
    #    return '%s' % self.to_dict()

    def get_args(self):
        """ Return exception arguments. """
        return self.args

    def get_error_code(self):
        """ Return error code. """
        return self.code

    def get_error_message(self):
        """ Return exception error. """
        return "%s" % (self.args)

    def get_class_name(self):
        """ Return class name. """
        return "%s" % (self.__class__.__name__)

    def to_dict(self):
        return { 'error_message' : '%s' % self.args, 
                 'error_code' : self.code, 
                 'class_name' : self.__class__.__name__ }

    def to_json(self):
        return json.dumps(self.to_dict())
