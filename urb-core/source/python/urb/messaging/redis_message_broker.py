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

class RedisMessageBroker(object):
    """ Message broker using Redis. The pubsub object returned by Redis
        is not thread safe, and hence subscribe/unsubscribe methods should
        not be used from different threads.
    """

    PROCESSING_SUFFIX = ".processing"

    # Our processing list will be sorted newest to oldest
    # We need to add them back in the proper order with
    # newest first in the processing list (lpop rpush)
    RESTORE_LOST_MESSAGES = """
local value = redis.call( 'LPOP', KEYS[1] )
local i = 0
while value do
    redis.call( 'RPUSH', KEYS[2], value )
    value = redis.call( 'LPOP', KEYS[1] )
    i = i + 1
end
return i
    """

    def __init__(self, **kwargs):
        self.__redis = self.configure_redis(**kwargs)
        # Register our script
        self.__restore_lost_messages = self.__redis.register_script(RedisMessageBroker.RESTORE_LOST_MESSAGES)

    def configure_redis(self, **kwargs):
        # Direct server connection
        # Default connection parameters: 
        #    host='localhost', port=6379, db=0
        return redis.StrictRedis(**kwargs)

    def get_connection_pool(self, **kwargs):
        return self.__redis.ConnectionPool(**kwargs)

    def get_connection_port(self):
        return self.__redis.connection_pool.connection_kwargs.get('port')

    def get_connection_host(self):
        return self.__redis.connection_pool.connection_kwargs.get('host')

    def __get_pub_sub(self):
        if self.__pub_sub is None:
            self.__pub_sub = self.__redis.pubsub()
        return self.__redis.pubsub()

    def subscribe(self, channel_name, message_handler):
        """ Subscribe message handler to the given channel. 
            Note that redis pubsub object is not thread safe. 
        """
        self.__get_pub_sub().subscribe(**{channel_name : message_handler})

    def unsubscribe(self, channel_name):
        """ Unsubscribe message handler from the given channel.
            Note that redis pubsub object is not thread safe. 
        """
        self.__get_pub_sub().unsubscribe(channel_name)

    def create_queue(self, queue_name):
        """ Create queue. """
        pass

    def delete_queue(self, queue_name):
        """ Delete queue. """
        self.__redis.delete(queue_name)
        self.__redis.delete(queue_name+RedisMessageBroker.PROCESSING_SUFFIX)

    def clear_queue(self, queue_name):
        """ Clear queue. """
        self.__redis.delete(queue_name)

    def get_queue_size(self, queue_name):
        """ Return queue size. """
        return self.__redis.llen(queue_name)

    def is_queue_empty(self, queue_name):
        """ Return True if queue is empty, False otherwise. """
        return self.get_queue_size(queue_name) == 0

    def push(self, queue_name, message):
        """ Put message into the queue. """
        self.__redis.lpush(queue_name, message)

    def push_with_score(self, queue_name, score, message):
        """ Put message into the queue with a score. """
        self.__redis.zadd(queue_name, score, message)

    def pop_score_range(self, queue_name, max_score):
        """ Pop messages the queue within score range. """
        item_list = self.__redis.zrangebyscore(queue_name, 0, max_score)
        self.__redis.zremrangebyscore(queue_name, 0, max_score)
        return item_list

    def pop_blocking(self, queue_name, timeout=0):
        """ Remove and return message from the queue. 
            Block until message is available, or until timeout.
        """
        m = self.__redis.brpoplpush(queue_name, queue_name+RedisMessageBroker.PROCESSING_SUFFIX, timeout=timeout)
        if m:
            return (queue_name,m)
        return None

    def pop(self, queue_name):
        """ Remove and return message from the queue. 
            Do not block.
        """
        return self.__redis.rpoplpush(queue_name,queue_name+RedisMessageBroker.PROCESSING_SUFFIX)

    def message_processed(self, queue_name, m):
        self.__redis.lrem(queue_name+RedisMessageBroker.PROCESSING_SUFFIX, 0, m)

    def restore_lost_messages(self, queue_name):
        return self.__restore_lost_messages(keys=[queue_name+RedisMessageBroker.PROCESSING_SUFFIX,queue_name])

    def determine_master_message_broker(self, key, value=None, ttl=60):
        master_broker = self.__redis.get(key)

        if master_broker is None and value is not None:
            # No master broker and the caller wants to be the master if none
            # exists

            # Try and become the master broker
            ret = self.__redis.set(key,value,nx=True,ex=ttl)
            if ret:
                # We are now the master broker...
                master_broker = value
            else:
                # Someone must have beat us to it...
                master_broker = self.__redis.get(key)
        return master_broker

    def refresh_master_message_broker(self, key, ttl=60):
        self.__redis.expire(key, ttl)

    def get_unique_channel_name(self, base_name):
        """ Form unique channel name. """
        id = self.__redis.incr('%s.id' % base_name)
        return '%s.%s' % (base_name, id)

    def get_channel_names(self, name_pattern):
        """ Return list of known channel names. """
        return self.__redis.keys(name_pattern)

# Testing
if __name__ == '__main__':
    rmb = RedisMessageBroker()
    message = 'XYZ'
    q_name = 'xyz'
    print('Delete Q')
    rmb.delete_queue(q_name)
    print('Q Size: ', rmb.get_queue_size(q_name))
    rmb.push(q_name, message)
    print('Pushed: ', message)
    print('Q Size: ', rmb.get_queue_size(q_name))
    message = rmb.pop_blocking(q_name)
    print('Popped: ', message)
    print('Q Size: ', rmb.get_queue_size(q_name))
    print('Channel list: ', rmb.get_channel_names('*.notify'))
    # Processing test
    p_queue = 'ptest'
    rmb.delete_queue(p_queue)
    rmb.push(p_queue, 'a')
    rmb.push(p_queue, 'b')
    rmb.push(p_queue, 'c')
    # Should print a
    print(rmb.pop_blocking(p_queue,1))
    # Should print b
    print(rmb.pop_blocking(p_queue,1))
    # Now restore... Should print 2
    print(rmb.restore_lost_messages(p_queue)(
    # Should print a
    print(rmb.pop_blocking(p_queue,1))
    # Should print b
    print(rmb.pop_blocking(p_queue,1))
    # Should print c
    print(rmb.pop_blocking(p_queue,1))
