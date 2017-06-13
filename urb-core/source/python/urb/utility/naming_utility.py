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


#import re

class NamingUtility:

    @classmethod
    def create_slave_id(cls, job_id, task_id="undefined", channel_name='urb.endpoint.x.notify'):
#        jid= re.sub('[-.]', '', str(job_id))
        return "slave-" + job_id + "." + str(task_id) + ":" + str(channel_name)

    @classmethod
    def get_job_id_from_slave_id(cls, slave_id_value):
        digital_job_id = False
        beg = slave_id_value.find('-')
        if beg == -1:
            return None
        end = slave_id_value.find('.', beg)
        if end == -1:
            return None
        job_id = slave_id_value[beg+1:end]
        return job_id
