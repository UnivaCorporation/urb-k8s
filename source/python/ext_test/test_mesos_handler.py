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


import gevent
import json
import sys
import os

# add path to test util
sys.path.append('../../urb-core/source/python/test')
# add path to urb
sys.path.append('../../urb-core/source/python')

from common_utils import needs_setup
from common_utils import needs_cleanup
from common_utils import create_service_thread
from common_utils import create_service_channel

from urb.messaging.channel_factory import ChannelFactory
from urb.messaging.channel import Channel

if os.environ.get("URB_CONFIG_FILE") is None:
    raise Exception("URB_CONFIG_FILE environment variable has to be defined")

SERVICE_THREAD = create_service_thread(serve_time=10)
SERVICE_CHANNEL = create_service_channel('urb.endpoint.0.mesos')


@needs_setup
def test_setup():
    print 'Starting service thread'
    SERVICE_CHANNEL.clear()
    SERVICE_THREAD.start()

def test_register_framework():
    print 'Creating service and client channels'
    client_channel_name = 'urb.endpoint.1.notify'
    channel_factory = ChannelFactory.get_instance()
    client_channel = channel_factory.create_channel(client_channel_name)
    client_channel.clear()
    framework = {}
    framework['name'] = 'TestFrameworkC++'
    register_msg = {}
    register_msg['framework'] = framework
    payload = {'mesos.internal.RegisterFrameworkMessage' : register_msg}

    msg = {'target' : 'RegisterFrameworkMessage', 
           'reply_to' : client_channel_name,
           'source_id' : 'urb.endpoint.1',
           'payload' : payload,
          }
    print 'Writing register framework message'
    SERVICE_CHANNEL.write(json.dumps(msg))
    msg2 = client_channel.read_blocking(timeout=5)
    print 'Service response: ', msg2
    assert msg2 != None
    msg2 = json.loads(msg2[1])
    # Allow errors temporarily until UGE test config is done
    assert (msg2.get('payload') != None or msg2.get('error') != None)

def test_authenticate():
    msg = {'target' : 'AuthenticateMessage', 
           'source_id' : 'urb.endpoint.1',
          }
    SERVICE_CHANNEL.write(json.dumps(msg))

def test_deactivate_framework():
    msg = {'target' : 'DeactivateFrameworkMessage', 
           'source_id' : 'urb.endpoint.1',
          }
    SERVICE_CHANNEL.write(json.dumps(msg))

def test_framework_to_executor():
    msg = {'target' : 'ExitedExecutorMessage', 
           'source_id' : 'urb.endpoint.1',
          }
    SERVICE_CHANNEL.write(json.dumps(msg))

def test_framework_to_executor():
    msg = {'target' : 'FrameworkToExecutorMessage', 
           'source_id' : 'urb.endpoint.1',
          }
    SERVICE_CHANNEL.write(json.dumps(msg))

def test_kill_task():
    msg = {'target' : 'KillTaskMessage', 
           'source_id' : 'urb.endpoint.1',
          }
    SERVICE_CHANNEL.write(json.dumps(msg))

def test_launch_tasks():
    framework_id = {}
    framework_id['value'] = 'framework-1'
    message = {}
    message['framework_id'] = framework_id
    payload = {}
    payload['mesos.internal.LaunchTasksMessage'] = message
    urb_message = {
           'target' : 'LaunchTasksMessage',
           'source_id' : 'urb.endpoint.1',
           'payload' : payload,
    }
    print 'Writing launch tasks message'
    SERVICE_CHANNEL.write(json.dumps(urb_message))

def test_reconcile_tasks():
    msg = {'target' : 'ReconcileTasksMessage', 
           'source_id' : 'urb.endpoint.1',
          }
    SERVICE_CHANNEL.write(json.dumps(msg))

def test_register_slave():
    msg = {'target' : 'RegisterSlaveMessage', 
           'source_id' : 'urb.endpoint.1',
          }
    SERVICE_CHANNEL.write(json.dumps(msg))

def test_reregister_framework():
    msg = {'target' : 'ReregisterFrameworkMessage', 
           'source_id' : 'urb.endpoint.1',
          }
    SERVICE_CHANNEL.write(json.dumps(msg))

def test_reregister_slave():
    msg = {'target' : 'ReregisterSlaveMessage', 
           'source_id' : 'urb.endpoint.1',
          }
    SERVICE_CHANNEL.write(json.dumps(msg))

def test_resource_request():
    msg = {'target' : 'ResourceRequestMessage', 
           'source_id' : 'urb.endpoint.1',
          }
    SERVICE_CHANNEL.write(json.dumps(msg))

def test_revive_offers():
    msg = {'target' : 'ReviveOffersMessage', 
           'source_id' : 'urb.endpoint.1',
          }
    SERVICE_CHANNEL.write(json.dumps(msg))

def test_status_update_acknowledgement():
    msg = {'target' : 'StatusUpdateAcknowledgementMessage', 
           'source_id' : 'urb.endpoint.1',
          }
    SERVICE_CHANNEL.write(json.dumps(msg))

def test_status_update():
    msg = {'target' : 'StatusUpdateMessage', 
           'source_id' : 'urb.endpoint.1',
          }
    SERVICE_CHANNEL.write(json.dumps(msg))

def test_submit_scheduler_request():
    msg = {'target' : 'SubmitSchedulerRequest', 
           'source_id' : 'urb.endpoint.1',
          }
    SERVICE_CHANNEL.write(json.dumps(msg))

def test_unregister_framework():
    msg = {'target' : 'UnregisterFrameworkMessage', 
           'source_id' : 'urb.endpoint.1',
          }
    SERVICE_CHANNEL.write(json.dumps(msg))


def test_unregister_slave():
    msg = {'target' : 'UnregisterSlaveMessage', 
           'source_id' : 'urb.endpoint.1',
          }
    SERVICE_CHANNEL.write(json.dumps(msg))

@needs_cleanup
def test_cleanup():
    # Try and signal a shutdown but just wait for the timeout if it fails
    try:
        from urb.service.urb_service_controller import URBServiceController
        from gevent import monkey; monkey.patch_socket()
        controller = URBServiceController('urb.service.monitor')
        controller.send_shutdown_message()
    except:
        pass
    SERVICE_THREAD.join()

# Testing
if __name__ == '__main__':
    test_setup()
    test_register_framework()
    test_cleanup()
    pass
