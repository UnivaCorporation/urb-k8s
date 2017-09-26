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

FROM local/urb-bin-base

# copy Python eggs
COPY urb-core/dist/urb-*-py2.7/*.egg /tmp/
COPY urb-core/dist/urb-*-py2.7-redhat_7-linux-x86_64/*.egg /tmp/
COPY urb-core/dist/urb-*/pkg/urb-*-py2.7.egg /tmp/

# install all required Python dependencies, Mesos eggs
RUN easy_install /tmp/google_common-*-py2.7.egg \
                 /tmp/xmltodict-*-py2.7.egg \
                 /tmp/sortedcontainers-*-py2.7.egg \
                 /tmp/redis-*-py2.7.egg \
                 /tmp/pymongo-*-py2.7-linux-x86_64.egg \
                 /tmp/greenlet-*-py2.7-linux-x86_64.egg \
                 /tmp/gevent-*-py2.7-linux-x86_64.egg \
                 /tmp/mesos.scheduler-*-py2.7-linux-x86_64.egg \
                 /tmp/mesos.executor-*-py2.7-linux-x86_64.egg \
                 /tmp/mesos.native-*-py2.7.egg \
                 /tmp/mesos.interface-*-py2.7.egg \
                 /tmp/mesos-1.1.0-py2.7.egg
 
