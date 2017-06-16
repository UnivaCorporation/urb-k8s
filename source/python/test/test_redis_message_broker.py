#!/usr/bin/env python

import time

from common_utils import needs_config
from common_utils import needs_setup
from common_utils import needs_cleanup
from common_utils import needs_redis

from urb.messaging.redis_message_broker import RedisMessageBroker

TEST_QUEUE = "test_q"


@needs_setup
def test_setup():
    pass

@needs_redis
def test_constructor():
    rmb = RedisMessageBroker()
    return rmb

@needs_redis
def test_delete_queue():
    rmb = RedisMessageBroker()
    rmb.delete_queue(TEST_QUEUE)

@needs_redis
def test_create_queue():
    rmb = RedisMessageBroker()
    rmb.delete_queue(TEST_QUEUE)
    rmb.create_queue(TEST_QUEUE)
    size = rmb.get_queue_size(TEST_QUEUE)
    print 'Test Queue Size: ', size
    assert size == 0

@needs_redis
def test_push_pop():
    rmb = RedisMessageBroker()
    rmb.create_queue(TEST_QUEUE)
    size = rmb.get_queue_size(TEST_QUEUE)
    msg = "My Test Message"
    rmb.push(TEST_QUEUE, msg)
    print 'Pushed message: ', msg
    size2 = rmb.get_queue_size(TEST_QUEUE)
    assert size2 == size+1 
    msg2 = rmb.pop(TEST_QUEUE)
    print 'Popped message: ', msg2
    assert msg2 == msg
    rmb.delete_queue(TEST_QUEUE)
    size3 = rmb.get_queue_size(TEST_QUEUE)
    assert size3 == size

@needs_redis
def test_push_many():
    rmb = RedisMessageBroker()
    rmb.create_queue(TEST_QUEUE)
    size = rmb.get_queue_size(TEST_QUEUE)
    n_messages = 100000
    t0 = time.time()
    for m in range (0,n_messages):
        msg = "My Test Message %s" % m
        rmb.push(TEST_QUEUE, msg)
    t1 = time.time()
    print 'Pushed %s messages in %s seconds' % (n_messages, t1-t0)
    size2 = rmb.get_queue_size(TEST_QUEUE)
    assert size2 == size+n_messages 
    rmb.delete_queue(TEST_QUEUE)

@needs_cleanup
def test_cleanup():
    pass

