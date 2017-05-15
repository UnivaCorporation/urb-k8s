#!/bin/bash
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

set -e
sudo easy_install virtualenv
VENV_NAME=${1:-venv}
virtualenv $VENV_NAME
. $VENV_NAME/bin/activate
easy_install dist/urb-1.4.2-py2.7/argparse-1.4.0-py2.7.egg dist/urb-1.4.2-py2.7/google_common-0.0.1-py2.7.egg dist/urb-1.4.2-py2.7/redis-2.10.3-py2.7.egg dist/urb-1.4.2-py2.7/xmltodict-0.9.1-py2.7.egg dist/urb-1.4.2-py2.7/sortedcontainers-0.9.4-py2.7.egg dist/urb-1.4.2-py2.7-redhat_7-linux-x86_64/pymongo-2.8-py2.7-linux-x86_64.egg dist/urb-1.4.2-py2.7-redhat_7-linux-x86_64/gevent-1.1.2-py2.7-linux-x86_64.egg dist/urb-1.4.2-py2.7-redhat_7-linux-x86_64/greenlet-0.4.10-py2.7-linux-x86_64.egg dist/urb-1.4.2-py2.7-redhat_7-linux-x86_64/mesos.* dist/urb-1.4.2-py2.7/mesos.native-1.1.0-py2.7.egg dist/urb-1.4.2-py2.7/mesos.interface-1.1.0-py2.7.egg dist/urb-1.4.2-py2.7/mesos-1.1.0-py2.7.egg dist/urb-1.4.2/pkg/urb-1.4.2-py2.7.egg
deactivate


