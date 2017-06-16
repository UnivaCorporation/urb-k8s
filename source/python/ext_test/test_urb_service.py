#!/usr/bin/env python
import sys
import os
# add path to test util
sys.path.append('../../urb-core/source/python/test')
# add path to urb
sys.path.append('../../urb-core/source/python')

from common_utils import remove_test_log_file
from urb.service.urb_service import URBService

if os.environ.get("URB_CONFIG_FILE") is None:
    raise Exception("URB_CONFIG_FILE environment variable has to be defined")

def test_setup():
    pass

def test_constructor():
    urb_service = URBService(skip_cmd_line_config=True)
    assert isinstance(urb_service, URBService)

def test_serve():
    urb_service = URBService(skip_cmd_line_config=True)
    urb_service.serve(3)
    #urb_service.shutdown_callback()

def test_cleanup():
    remove_test_log_file()

# Testing
if __name__ == '__main__':
    pass
