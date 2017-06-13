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

# set environment variables copy binary files
RUN mkdir -p /opt/urb/lib
COPY urb-core/dist/urb-*-linux-x86_64/lib/linux-x86_64/liburb.* /opt/urb/lib/
ENV LD_LIBRARY_PATH=/opt/urb/lib:$LD_LIBRARY_PATH
ENV URB_MASTER=urb://urb.default:6379
RUN mkdir -p /opt/urb/bin
COPY urb-core/dist/urb-*-linux-x86_64/share/examples/frameworks/linux-x86_64/example_*.test /opt/urb/bin/

# for testing purposes add redis command line tool
COPY urb-core/dist/urb-*-linux-x86_64/bin/linux-x86_64/redis-cli /opt/urb/bin/

ENTRYPOINT ["/opt/urb/bin/example_framework.test"]
