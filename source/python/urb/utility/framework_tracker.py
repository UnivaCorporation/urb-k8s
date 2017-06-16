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


from collections import deque
from object_tracker import ObjectTracker

class FrameworkTracker(ObjectTracker):

    MAX_NUMBER_OF_FINISHED_FRAMEWORKS = 25

    def __init__(self):
        ObjectTracker.__init__(self)
        self.framework_id_dict = {}
        self.finished_framework_id_deque = deque([],FrameworkTracker.MAX_NUMBER_OF_FINISHED_FRAMEWORKS)
        self.finished_framework_dict = {}

    def get_framework_and_store_request_framework_id(self, request, framework_id):
        self.store_request_framework_id(request, framework_id)
        return self.get(framework_id)

    def store_request_framework_id(self, request, framework_id):
        message_id = request.get('message_id')
        if message_id is not None:
            self.framework_id_dict[message_id] = framework_id

    def retrieve_and_forget_request_framework_id(self, request):
        message_id = request.get('message_id')
        if message_id is None:
            return None
        framework_id = self.framework_id_dict.get(message_id)
        if framework_id is not None:
            del self.framework_id_dict[message_id]
        return framework_id

    def remove(self, id):
        framework = ObjectTracker.remove(self, id)
        if framework is not None:
            self.finished_framework_dict[id] = framework
            if len(self.finished_framework_id_deque) == FrameworkTracker.MAX_NUMBER_OF_FINISHED_FRAMEWORKS:
                clear_framework_id = self.finished_framework_id_deque.popleft()
                del self.finished_framework_dict[clear_framework_id] 
            self.finished_framework_id_deque.append(id)
        return framework

    def get_active_or_finished_framework(self, id):
        framework = self.get(id)
        if framework is None:
            framework = self.finished_framework_dict.get(id)
        return framework

    def is_framework_finished(self, id):
        return self.finished_framework_dict.has_key(id)

# Testing
if __name__ == '__main__':
    class Test:
        pass

    ft = FrameworkTracker.get_instance()
    #x = Test()
    #ft.store_request_framework_id(x, {'one' : 1})
    #print ft.retrieve_and_forget_request_framework_id(x) 
    #print ft.object_dict.iteritems() 
    #print ft
    for i in range(0,30):
        f = {'id' : i}
        ft.add(i,f)
    print ft.object_dict
    print 'Removing items'

    for i in range(0,30):
        print 'Removing id: ', i
        f = ft.remove(i)
        print 'Removed: ', f
        f2 = ft.get(i)
        print 'Active: ', f2
        f3 = ft.get_active_or_finished_framework(i)
        print 'Active/Finished: ', f3
    print 'Active: ', ft.object_dict
    print 'Finished: ', ft.finished_framework_dict
    for i in range(0,30):
        print i, ' is finished? ', ft.is_framework_finished(i)
        


