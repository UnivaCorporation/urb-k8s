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


from common_utils import needs_config
from common_utils import needs_setup
from common_utils import needs_cleanup

from urb.messaging.channel_factory import ChannelFactory
from urb.messaging.channel import Channel

@needs_setup
def test_setup():
    pass

@needs_config
def test_constructor():
    channel_factory = ChannelFactory.get_instance()
    assert isinstance(channel_factory, ChannelFactory)

@needs_config
def test_create_channel():
    channel_factory = ChannelFactory.get_instance()
    channel = channel_factory.create_channel('test_channel')
    assert isinstance(channel, Channel)

@needs_cleanup
def test_cleanup():
    pass

# Testing
if __name__ == '__main__':
    pass
