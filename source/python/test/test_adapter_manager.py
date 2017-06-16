#!/usr/bin/env python


from common_utils import needs_config
from common_utils import needs_setup
from common_utils import needs_cleanup

from urb.adapters.adapter_manager import AdapterManager

@needs_setup
def test_setup():
    pass

@needs_config
def test_constructor():
    adapter_manager = AdapterManager.get_instance()
    assert isinstance(adapter_manager, AdapterManager)

@needs_cleanup
def test_cleanup():
    pass

# Testing
if __name__ == '__main__':
    pass
