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

FROM centos:7

# install epel
RUN yum install -y http://dl.fedoraproject.org/pub/epel/epel-release-latest-$(awk '/^%rhel/ { print $2 }' /etc/rpm/macros.dist).noarch.rpm

# install binary dependencies
RUN yum update -y; yum install -y libev libuuid zlib python-setuptools; yum clean all

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

# set environment variables copy files
RUN mkdir -p /opt/urb/lib
COPY urb-core/dist/urb-*-linux-x86_64/lib/linux-x86_64/liburb.* /opt/urb/lib/
ENV LD_LIBRARY_PATH=/opt/urb/lib:$LD_LIBRARY_PATH
RUN mkdir -p /opt/urb/bin
COPY urb-core/dist/urb-*/share/examples/frameworks/python/*.py /opt/urb/bin/
ENTRYPOINT ["/opt/urb/bin/test_framework.py", "urb://urb.default:6379"]

 
