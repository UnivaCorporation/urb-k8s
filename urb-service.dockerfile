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
RUN yum update -y; yum install -y libev libuuid zlib libyaml python-setuptools; yum clean all

RUN easy_install kubernetes==2.0.0 # temporary indicate stable version

# copy urb-core Python eggs
COPY urb-core/dist/urb-*-py2.7/*.egg /tmp/
COPY urb-core/dist/urb-*-py2.7-redhat_7-linux-x86_64/*.egg /tmp/
COPY urb-core/dist/urb-*/pkg/urb-*-py2.7.egg /tmp/

# for testing purposes add redis command line tool
COPY urb-core/dist/urb-*-linux-x86_64/bin/linux-x86_64/redis-cli /tmp

# copy k8s adapter Python egg
COPY source/python/dist/k8s_adapter-*-py2.7.egg /tmp/

# install all required Python dependencies, Mesos and URB eggs
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
                 /tmp/mesos-1.1.0-py2.7.egg \
                 /tmp/urb-*-py2.7.egg \
                 /tmp/k8s_adapter-*-py2.7.egg

# set environment variables required by URB service and copy configuration files
ENV URB_ROOT=/urb
RUN mkdir -p $URB_ROOT
ENV URB_CONFIG_FILE=$URB_ROOT/etc/urb.conf
RUN mkdir -p $URB_ROOT/etc
COPY etc/urb.conf $URB_CONFIG_FILE
COPY etc/urb.executor_runner.conf $URB_ROOT/etc
EXPOSE 6379

ENTRYPOINT ["/usr/bin/urb-service"]

