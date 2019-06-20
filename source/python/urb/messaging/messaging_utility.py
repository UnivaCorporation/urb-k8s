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

import uuid

class MessagingUtility:
  
    @classmethod
    def get_notify_channel_name(cls, reply_to, endpoint_id):
        notify_channel_name = reply_to
        if notify_channel_name is None:
            if endpoint_id is not None:
                notify_channel_name = 'urb.endpoint.%s.notify' % endpoint_id
        return notify_channel_name

    @classmethod
    def get_endpoint_id(cls, channel_name):
        """ 
            Return endpoint id from channel name: 
                urb.endpoint.<endpoint_id>....
        """
        if channel_name:
            if channel_name.startswith('urb.endpoint.'):
                return channel_name.split('.')[2]
            else:
                return None
        else:
            return uuid.uuid1().hex

# Testing
if __name__ == '__main__':
    reply_to = None
    some_complex_variable = 53
    print(MessagingUtility.get_notify_channel_name(reply_to, some_complex_variable))
    print(MessagingUtility.get_endpoint_id('urb.endpoint.27.notify'))
    print(MessagingUtility.get_endpoint_id('invalid.notify'))
