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
