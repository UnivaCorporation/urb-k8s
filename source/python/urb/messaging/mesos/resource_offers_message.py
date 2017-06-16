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


from urb.messaging.message import Message
from urb.constants import mesos_messages 

class ResourceOffersMessage(Message):

    def __init__(self, source_id, payload, payload_type='json'):
        Message.__init__(
            self, 
            target=mesos_messages.MESOS_RESOURCE_OFFERS_MESSAGE,
            source_id=source_id,
            payload=payload,
            payload_type=payload_type
        )

    @classmethod
    def target(cls):
        return mesos_messages.MESOS_RESOURCE_OFFERS_MESSAGE
