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


class NamingUtility:

    @classmethod
    def create_slave_id(cls, job_id, task_id="undefined", channel_name='urb.endpoint.x.notify'):
        return "slave-"+str(job_id)+"."+str(task_id)+":"+str(channel_name)

    @classmethod
    def get_job_id_from_slave_id(cls, slave_id_value):
        beg = slave_id_value.find('-')
        if beg == -1:
            return None
        end = slave_id_value.find('.', beg)
        if end == -1:
            return None
        job_id = slave_id_value[beg+1:end]
        if job_id.isdigit():
            return job_id
        return None

#    @classmethod
#    def get_job_id_from_slave_id(cls, slave_id_value):
#        lst = slave_id_value.split('-')
#        if len(lst) != 0:
#            lst1 = lst[1].split(':')
#            if len(lst1) != 0:
#                job_id = lst1[0]
#                slave_job_id[:slave_job_id.index('.')]
#                return job_id
#        return None

#    @classmethod
#    def get_job_id_from_slave_id(cls, slave_id_value):
#        job_id = slave_id_value[slave_id_value.index('-')+1:slave_id_value.index(':')]
#        return job_id
