#!/usr/bin/env python
# ___INFO__MARK_BEGIN__
# ############################################################################
#
# This code is the Property, a Trade Secret and the Confidential Information
#  of Univa Corporation.
#
#  Copyright Univa Corporation. All Rights Reserved. Access is Restricted.
#
#  It is provided to you under the terms of the
#  Univa Term Software License Agreement.
#
#  If you have any questions, please contact our Support Department.
#
#  www.univa.com
#
###########################################################################
#___INFO__MARK_END__


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

