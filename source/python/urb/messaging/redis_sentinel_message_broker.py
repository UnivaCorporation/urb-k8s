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


import redis
from redis.sentinel import Sentinel
from urb.messaging.redis_message_broker import RedisMessageBroker
from urb.exceptions.configuration_error import ConfigurationError

class RedisSentinelMessageBroker(RedisMessageBroker):
    """ Redis Sentinel Message broker. 
    """

    def __init__(self, **kwargs):
        self.init_sentinel(**kwargs)
        RedisMessageBroker.__init__(self, **kwargs)

    def init_sentinel(self, **kwargs):
        if not kwargs.has_key('sentinel_servers'):
            raise ConfigurationError('Kewyword sentinel_servers is missing.')
        if not kwargs.has_key('sentinel_master'):
            raise ConfigurationError('Kewyword sentinel_master is missing.')
 
        # Enable sentinel support
        self.__sentinel_servers = kwargs['sentinel_servers']
        self.__sentinel_master = kwargs['sentinel_master']
        del kwargs['sentinel_servers']
        del kwargs['sentinel_master']
        self.__sentinel = Sentinel(self.__sentinel_servers, **kwargs)

    def configure_redis(self, **kwargs):
        return self.__sentinel.master_for(self.__sentinel_master)

    def get_connection_port(self):
        return self.__sentinel.discover_master(self.__sentinel_master)[1]

    def get_connection_host(self):
        return self.__sentinel.discover_master(self.__sentinel_master)[0]

# Testing
if __name__ == '__main__':
    rmb = RedisSentinelMessageBroker(sentinel_servers=[('localhost',6379)],sentinel_master='localhost')
    message = 'XYZ'
    q_name = 'xyz'
    print 'Delete Q'
    rmb.delete_queue(q_name)
    print 'Q Size: ', rmb.get_queue_size(q_name)
    rmb.push(q_name, message)
    print 'Pushed: ', message
    print 'Q Size: ', rmb.get_queue_size(q_name)
    message = rmb.pop_blocking(q_name)
    print 'Popped: ', message
    print 'Q Size: ', rmb.get_queue_size(q_name)
    print 'Channel list: ', rmb.get_channel_names('*.notify')
