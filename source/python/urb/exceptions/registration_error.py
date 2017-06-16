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


from urb.exceptions.urb_exception import URBException
from urb.constants import urb_status

class RegistrationError(URBException):
    """ Configuration error class. """
    def __init__(self, error="", **kwargs):
        URBException.__init__(
            self, error, urb_status.URB_REGISTRATION_ERROR,
            **kwargs)
