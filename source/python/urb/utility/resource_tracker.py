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


from object_tracker import ObjectTracker

class ResourceTracker(ObjectTracker):

    def __init__(self):
        self.last_offer_id = 0

    def get_unique_offer_id(self):
        self.last_offer_id += 1
        return self.last_offer_id 

# Testing
if __name__ == '__main__':
    rt = ResourceTracker.get_instance()
    print rt 

