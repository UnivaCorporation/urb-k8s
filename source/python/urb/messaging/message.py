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


import UserDict
import json

class Message(UserDict.UserDict):

    def __init__(self, target=None, source_id=None, payload={}, payload_type='json', message_dict=None):
        # Initialize straight from dict
        if message_dict is not None:
            UserDict.UserDict.__init__(self, message_dict)
            return

        # Initialize from source_id, target, payload, etc.
        UserDict.UserDict.__init__(self)
        if source_id is not None:
            self['source_id'] = source_id
        if target is not None:
            self['target'] = target
        self['payload'] = payload
        self['payload_type'] = payload_type

    def to_dict(self):
        return self.data

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_string):
        message_dict = json.loads(json_string)
        return Message(message_dict=message_dict)

    def get_source(self):
        return self.get('source_id')

    def get_target(self):
        return self.get('target')

# Testing
if __name__ == '__main__':
    m = Message('a.b.c', 'HelloMessage', payload={'x' : 'X'})
    print m
    print json.dumps(m.to_dict())
