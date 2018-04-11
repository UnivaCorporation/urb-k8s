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


import sys
import gevent
import json

# add path to test util
sys.path.append('../../urb-core/source/python/test')
# add path to urb
sys.path.append('../../urb-core/source/python')

from common_utils import needs_setup
from common_utils import needs_cleanup
from common_utils import create_service_thread

from urb.messaging.channel_factory import ChannelFactory
from urb.messaging.channel import Channel

@needs_setup
def test_setup():
    pass

def test_ping():
    service_thread = create_service_thread(serve_time=3)
    print 'Starting service thread'
    service_thread.start()
    gevent.sleep(2)
    print 'Creating service and client channels'
    channel_factory = ChannelFactory.get_instance()
    service_channel = channel_factory.create_channel('urb.service.monitor')
    client_channel_name = 'urb.client.response'
    client_channel = channel_factory.create_channel(client_channel_name)
    client_channel.clear()
    msg = {'target' : 'PingMessage', 'reply_to' : client_channel_name}
    print 'Writing ping message'
    service_channel.write(json.dumps(msg))
    msg2 = client_channel.read_blocking(timeout=5)
    assert msg2 != None
    msg2 = json.loads(msg2[1])
    payload = msg2.get('payload')
    assert payload.get('ack') != None
    print 'Service response: ', payload.get('ack') 
    service_thread.urb_service.shutdown_callback()
    service_thread.join()

@needs_cleanup
def test_cleanup():
    pass

# Testing
if __name__ == '__main__':
    test_ping()
#    pass
