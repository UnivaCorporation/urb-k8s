#!/usr/bin/env python


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
