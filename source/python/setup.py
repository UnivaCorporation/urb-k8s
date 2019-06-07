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

from __future__ import with_statement, print_function
import sys

if "nosetests" in sys.argv:
    try:
        print ("Monkey patching thread")
        import gevent.monkey
        gevent.monkey.patch_thread()
        gevent.monkey.patch_socket()
    except Exception as ex:
        print(ex)

# Work around http://bugs.python.org/issue15881#msg170215
try:
    import multiprocessing
except ImportError:
    pass

try:
    from setuptools import setup
    extra = dict(include_package_data=True)
except ImportError:
    from distutils.core import setup
    extra = {}

import os

from urb import __version__

if sys.version_info <= (2, 5):
    error = "ERROR: URB requires Python Version 2.6 or above...exiting."
    print(error, file=sys.stderr)
    sys.exit(1)

if os.environ.get('USER','') == 'vagrant':
    del os.link

def readme():
    with open("README") as f:
        return f.read()

setup(name = 'urb',
      version = __version__,
      description = 'Universal Resource Broker',
      long_description = readme(),
      author = 'Univa',
      author_email = 'info@univa.com',
      entry_points = {
        'console_scripts': [
            'urb-service=urb.service.urb_service:run',
            'urb-service-controller=urb.service.urb_service_controller:run',
            'urb-executor-runner=urb.executor.executor_runner:run'
        ],
      },
      url = 'https://www.univa.com',
      packages = [ 
                  'urb', 
                  'urb/adapters', 
                  'urb/config', 
                  'urb/constants', 
                  'urb/db', 
                  'urb/exceptions', 
                  'urb/executor', 
                  'urb/log', 
                  'urb/messaging', 
                  'urb/messaging/mesos', 
                  'urb/service',
                  'urb/utility'
      ],
      install_requires = [ 'redis','pymongo','sortedcontainers','xmltodict','gevent','greenlet' ],
      package_data = {
      },
      license = 'Univa',
      platforms = 'Posix; MacOS X',
      classifiers = [
                     'Intended Audience :: Developers',
                     'Operating System :: OS Independent',
                     'Programming Language :: Python :: 2',
                     'Programming Language :: Python :: 2.6',
                     'Programming Language :: Python :: 2.7',
                     ],
      **extra
      )
