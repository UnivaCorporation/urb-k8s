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
