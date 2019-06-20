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

import six
from choppyrange import ChoppyRange

class PortRangeUtility:

#        resource_ports = {}
#        resource_ports['name'] = "ports"
#        ranges = []
#        for begin,end in ports:
#            ranges.append({'begin': begin, 'end':end })
#        resource_ports['ranges'] = { 'range': ranges}
#        resource_ports['type'] = "RANGES"
#        resource_ports['role'] = "*"

    # if range comes as a string convert it to integer
    @classmethod
    def to_choppy_range_tuple(cls, port_range_dict):
        b = port_range_dict['begin']
        b_int = int(b) if isinstance(b, six.string_types) else b
        e = port_range_dict['end']
        e_int = int(b) if isinstance(e, six.string_types) else e
        return (e_int, e_int, 1)
            
    @classmethod
    def to_port_range(cls, choppy_range_tuple):
        return { 'begin' : choppy_range_tuple[0], 'end' : choppy_range_tuple[1] }

    @classmethod
    def to_choppy_range(cls, port_range_list):
        cr = ChoppyRange()
        for pr_dict in port_range_list:
            cr.insert(cls.to_choppy_range_tuple(pr_dict))
        return cr
            
    @classmethod
    def to_port_range_list(cls, choppy_range):
        port_range_list = []
        for pr in choppy_range.items():
            port_range_list.append(cls.to_port_range(pr))
        return port_range_list
            
    @classmethod
    def port_range_to_tuple_list(cls, port_range_list):
        tuple_list = []
        for pr_dict in port_range_list:
            tuple_list.append((pr_dict['begin'],pr_dict['end']))
        return tuple_list
            
    @classmethod
    def tuple_to_port_range_list(cls, tuple_list):
        port_range_list = []
        for t in tuple_list:
            port_range_list.append({'begin' : t[0], 'end' : t[1] })
        return port_range_list
            
    @classmethod
    def subtract(cls, port_range_list1, port_range_list2):
        choppy_range = cls.to_choppy_range(port_range_list1) 
        for pr_dict in port_range_list2:
            choppy_range.remove(cls.to_choppy_range_tuple(pr_dict))
        return cls.to_port_range_list(choppy_range)

    @classmethod
    def add(cls, port_range_list1, port_range_list2):
        choppy_range = cls.to_choppy_range(port_range_list1) 
        choppy_range.ignoreOverlaps = True
        for pr_dict in port_range_list2:
            choppy_range.insert(cls.to_choppy_range_tuple(pr_dict))
        return cls.to_port_range_list(choppy_range)

# Testing
if __name__ == '__main__':
     prl1 = [{'begin' : 10, 'end' : 20}, {'begin' : 30, 'end' : 40}] 
     prl2 = [{'begin' : 15, 'end' : 18}, {'begin' : 33, 'end' : 36}] 
     print('PRL1: ', PortRangeUtility.to_choppy_range(prl1))
     print('PRL2: ', PortRangeUtility.to_choppy_range(prl2))
     prl1m2 = PortRangeUtility.subtract(prl1,prl2)
     print('PRL1-PRL2: ', prl1m2)
     tprl1m2 = PortRangeUtility.port_range_to_tuple_list(prl1m2)
     print('PRL1-PRL2 as tuple list: ', tprl1m2)
     print('PRL1-PRL2 as port tuple list: ', PortRangeUtility.tuple_to_port_range_list(tprl1m2))
     print('PRL1+PRL2: ', PortRangeUtility.add(prl1,prl2))

