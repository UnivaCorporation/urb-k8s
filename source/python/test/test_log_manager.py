#!/usr/bin/env python

from common_utils import needs_config
from common_utils import needs_setup
from common_utils import needs_cleanup
from common_utils import read_last_log_line

from urb.config.config_manager import ConfigManager
from urb.log.log_manager import LogManager


@needs_setup
def test_setup():
    pass

@needs_config
def test_get_instance():
    lm = LogManager.get_instance()
    print 'LogManager instance: ', lm
    assert isinstance(lm, LogManager)

@needs_config
def test_check_instance():
    lm1 = LogManager.get_instance()
    lm2 = LogManager()
    print 'LogManager instance1: ', lm1
    print 'LogManager instance2: ', lm2
    assert lm1 == lm2

@needs_config
def test_trace_log():
    lm = LogManager.get_instance()
    lm.set_file_log_level('trace')
    logger = lm.get_logger('TraceLogger')
    log_msg = 'This is a trace log message'
    logger.trace(log_msg)
    last_log_line = read_last_log_line()
    print 'Looking for log message: ', log_msg
    print 'Last log line: ', last_log_line
    assert last_log_line.find(log_msg) >= 0

@needs_config
def test_debug_log():
    lm = LogManager.get_instance()
    logger = lm.get_logger('DebugLogger')
    log_msg = 'This is a debug log message'
    logger.debug(log_msg)
    last_log_line = read_last_log_line()
    print 'Looking for log message: ', log_msg
    print 'Last log line: ', last_log_line
    assert last_log_line.find(log_msg) >= 0

@needs_config
def test_warn_log():
    lm = LogManager.get_instance()
    logger = lm.get_logger('WarnLogger')
    log_msg = 'This is a warn log message'
    logger.warn(log_msg)
    last_log_line = read_last_log_line()
    print 'Looking for log message: ', log_msg
    print 'Last log line: ', last_log_line
    assert last_log_line.find(log_msg) >= 0

@needs_config
def test_info_log():
    lm = LogManager.get_instance()
    logger = lm.get_logger('WarnLogger')
    log_msg = 'This is an info log message'
    logger.info(log_msg)
    last_log_line = read_last_log_line()
    print 'Looking for log message: ', log_msg
    print 'Last log line: ', last_log_line
    assert last_log_line.find(log_msg) >= 0

@needs_config
def test_error_log():
    lm = LogManager.get_instance()
    logger = lm.get_logger('WarnLogger')
    log_msg = 'This is an error log message'
    logger.error(log_msg)
    last_log_line = read_last_log_line()
    print 'Looking for log message: ', log_msg
    print 'Last log line: ', last_log_line
    assert last_log_line.find(log_msg) >= 0

@needs_config
def test_critical_log():
    lm = LogManager.get_instance()
    logger = lm.get_logger('WarnLogger')
    log_msg = 'This is a critical log message'
    logger.critical(log_msg)
    last_log_line = read_last_log_line()
    print 'Looking for log message: ', log_msg
    print 'Last log line: ', last_log_line
    assert last_log_line.find(log_msg) >= 0


@needs_cleanup
def test_cleanup():
    pass

# Testing
if __name__ == '__main__':
    pass
