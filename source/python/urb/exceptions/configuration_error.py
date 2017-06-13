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


from urb.exceptions.urb_exception import URBException
from urb.constants import urb_status

class ConfigurationError(URBException):
    """ Configuration error class. """
    def __init__(self, error="", **kwargs):
        URBException.__init__(
            self, error, urb_status.URB_CONFIGURATION_ERROR,
            **kwargs)
