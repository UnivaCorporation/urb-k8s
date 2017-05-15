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



import time
import uuid
from urb.log.log_manager import LogManager

class EventDBInterface(object):
    """Class responsible for updating events in db."""

    def __init__(self, db_client):
        self.logger = LogManager.get_instance().get_logger(self.__class__.__name__)
        self.db_client = db_client

    def update_event(self, event_info):
        self.logger.debug('Updating event %s' % event_info)

        event_name = event_info.get('name', 'UnknownEvent')
        event_id = event_info.get('id')
        # remove event id before storing into db
        if event_id is not None:
            del event_info['id']
        else:
            event_id = uuid.uuid1()

        timestamp = time.time()
        event_info['timestamp'] = timestamp
        self.db_client.update('events',
            {'_id' : event_id},
            {'$set' : event_info}, upsert=True)
        # restore event id
        event_info['id'] = event_id

