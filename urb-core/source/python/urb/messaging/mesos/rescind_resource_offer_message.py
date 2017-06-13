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


from urb.messaging.message import Message
from urb.constants import mesos_messages 

class RescindResourceOfferMessage(Message):

    def __init__(self, source_id, payload, payload_type='json'):
        Message.__init__(
            self, 
            target=mesos_messages.MESOS_RESCIND_RESOURCE_OFFER_MESSAGE,
            source_id=source_id,
            payload=payload,
            payload_type=payload_type
        )

    @classmethod
    def target(cls):
        return mesos_messages.MESOS_RESCIND_RESOURCE_OFFER_MESSAGE
