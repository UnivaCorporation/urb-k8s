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


class ValueUtility:

    @classmethod
    def to_boolean(cls, value):
        s = '%s' % value
        if s.lower() in [ 'true', 't', '1', 'yes', 'y' ]:
            return True
        return False

 
