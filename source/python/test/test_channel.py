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

import os
import gevent

from common_utils import needs_config
from common_utils import needs_setup
from common_utils import needs_cleanup

from urb.messaging.channel_factory import ChannelFactory
from urb.messaging.channel import Channel

if os.environ.get("URB_CONFIG_FILE") is None:
    raise Exception("URB_CONFIG_FILE environment variable has to be defined")


@needs_setup
def test_setup():
    pass

@needs_config
def test_write_read():
    channel_factory = ChannelFactory.get_instance()
    channel = channel_factory.create_channel('test_channel')
    channel.clear()
    msg = 'test msg'
    print 'Writing message: ', msg
    channel.write(msg)
    msg2 = channel.read()
    if msg2:
        msg2 = msg2[1]
    print 'Read message: ', msg2
    assert msg2 == msg

@needs_config
def test_write_callback():
    channel_factory = ChannelFactory.get_instance()
    channel = channel_factory.create_channel('test_channel')
    channel.clear()
    class WriteCallback:
        def __init__(self):
            self.written_msg = None
        def write_callback(self, msg):
            print 'Entering write callback with message: ', msg
            self.written_msg = msg
    msg = 'test msg'
    write_callback = WriteCallback()
    channel.register_write_callback(write_callback.write_callback)
    channel.write(msg)
    gevent.sleep(0.001)
    assert write_callback.written_msg == msg

@needs_config
def test_read_callback():
    channel_factory = ChannelFactory.get_instance()
    channel = channel_factory.create_channel('test_channel')
    channel.clear()
    class ReadCallback:
        def __init__(self):
            self.read_msg = None
        def read_callback(self, msg):
            print 'Entering read callback with message: ', msg
            self.read_msg = msg[1]
    msg = 'test msg'
    read_callback = ReadCallback()
    channel.register_read_callback(read_callback.read_callback)
    channel.write(msg)
    channel.read()
    gevent.sleep(0.001)
    assert read_callback.read_msg == msg

@needs_config
def test_listen():

    # Try following:
    # 1) Service listens on service read channel
    # 2) Client writes on client write (service read) channel, 
    #    and enters write callback to listen on client read channel
    # 3) Service receives message on service read channel, 
    #    and enters read callback to write on service write (client read) 
    #    channel
    # 4) Client receives response message

    channel_factory = ChannelFactory.get_instance()
    service_read_channel = channel_factory.create_channel('urb.service.ping')
    client_write_channel = channel_factory.create_channel('urb.service.ping')

    service_write_channel = channel_factory.create_channel('urb.client.ping')
    client_read_channel = channel_factory.create_channel('urb.client.ping')

    client_read_channel.clear()
    service_read_channel.clear()
    class ClientWriteCallback:
        def __init__(self, response_channel):
            self.response_msg = None
            self.response_channel = response_channel
        def write_callback(self, msg):
            gevent.sleep(0.001)
            print 'Entering client write callback with message: ', msg
            self.response_msg = self.response_channel.read_blocking(timeout=1)
            if self.response_msg:
                self.response_msg = self.response_msg[1]
            print 'Exiting client write callback with response message: ', \
                self.response_msg
    cwc = ClientWriteCallback(client_read_channel)
    client_write_channel.register_write_callback(cwc.write_callback)

    class ServiceReadCallback:
        def __init__(self, response_channel):
            self.read_msg = None
            self.response_channel = response_channel
            self.response_msg = 'Ping Response'
        def read_callback(self, msg):
            print 'Entering service read callback with message: ', msg
            self.response_channel.write(self.response_msg)
            print 'Exiting service read callback with response message: ', \
                self.response_msg
    src = ServiceReadCallback(service_write_channel)
    service_read_channel.register_read_callback(src.read_callback)

    print 'Starting service listener'
    service_read_channel.start_listener()
    gevent.sleep(0.001)
    msg = 'Ping'
    print 'Writing client message'
    client_write_channel.write(msg)
    print 'Wrote client message, waiting for response'
    for i in range(0,1000):
        gevent.sleep(0.001)
        if cwc.response_msg is not None:
            break
    service_read_channel.stop_listener()
    assert cwc.response_msg == src.response_msg

@needs_cleanup
def test_cleanup():
    pass

# Testing
if __name__ == '__main__':
    import cProfile
    cProfile.run('test_listen()')
    pass
