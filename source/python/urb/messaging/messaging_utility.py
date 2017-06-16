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


class MessagingUtility:
  
    @classmethod
    def get_notify_channel_name(cls, reply_to, endpoint_id):
        notify_channel_name = reply_to
        if notify_channel_name is None:
            if endpoint_id is not None:
                notify_channel_name = 'urb.endpoint.%s.notify' % endpoint_id
        return notify_channel_name

    @classmethod
    def get_endpoint_id(cls, channel_name):
        """ 
            Return endpoint id from channel name: 
                urb.endpoint.<endpoint_id>....
        """
        if channel_name.startswith('urb.endpoint.'):
            return channel_name.split('.')[2]
        return None

# Testing
if __name__ == '__main__':
    reply_to = None
    some_complex_variable = 53
    print MessagingUtility.get_notify_channel_name(reply_to, some_complex_variable)
    print MessagingUtility.get_endpoint_id('urb.endpoint.27.notify')
    print MessagingUtility.get_endpoint_id('invalid.notify')
