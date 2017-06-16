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
from urb.constants import internal_messages 

class ServiceDisconnectedMessage(Message):

    def __init__(self, source_id, payload, payload_type='json'):
        Message.__init__(
            self, 
            target=internal_messages.SERVICE_DISCONNECTED_MESSAGE,
            source_id=source_id,
            payload=payload,
            payload_type=payload_type
        )

    @classmethod
    def target(cls):
        return internal_messages.SERVICE_DISCONNECTED_MESSAGE
