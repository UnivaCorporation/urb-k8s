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

import os
from common_utils import needs_config
from common_utils import needs_setup
from common_utils import needs_cleanup
from common_utils import read_last_log_line

from urb.config.config_manager import ConfigManager

if os.environ.get("URB_CONFIG_FILE") is None:
    raise Exception("URB_CONFIG_FILE environment variable has to be defined")

@needs_setup
def test_setup():
    pass

@needs_config
def test_get_instance():
    cm = ConfigManager.get_instance()
    print 'ConfigManager instance: ', cm
    assert isinstance(cm, ConfigManager)

@needs_config
def test_check_instance():
    cm1 = ConfigManager.get_instance()
    config_file1 = 'non-existent/file/path'
    cm1.set_config_file(config_file1)
    cm2 = ConfigManager()
    config_file2 = cm2.get_config_file()
    print 'ConfigManager instance1: ', cm1
    print 'ConfigManager instance2: ', cm2
    assert cm1 == cm2
    assert config_file1 == config_file2

@needs_config
def test_get_config_file():
    config_file = '/tmp/config'
    print 'Setting config file: ', config_file
    cm = ConfigManager.get_instance()
    cm.set_config_file(config_file)
    config_file2 = cm.get_config_file()
    print 'Got config file: ', config_file
    assert config_file == config_file2
    
@needs_config
def test_get_config_sections():
    cm = ConfigManager.get_instance()
    cm.set_config_file(os.environ.get("URB_CONFIG_FILE"))
    config_sections = cm.get_config_sections()
    print 'Got %s config sections: %s' % (len(config_sections), 
        config_sections)
    # this will throw exception if section is not there
    config_sections.index('Service')  
    assert len(config_sections) > 0

@needs_config
def test_get_config_option():
    cm = ConfigManager.get_instance()
    message_broker = cm.get_config_option('ChannelFactory', 'message_broker')
    print 'Got message broker: ', message_broker

@needs_cleanup
def test_cleanup():
    pass

# Testing
if __name__ == '__main__':
    test_get_config_sections()

