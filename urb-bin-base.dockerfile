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

# set environment variables, copy binaries
RUN mkdir -p /urb/lib
COPY urb-core/dist/urb-*-linux-x86_64/lib/linux-x86_64/liburb.* /urb/lib/
ENV LD_LIBRARY_PATH=/urb/lib:$LD_LIBRARY_PATH


# for testing purposes add redis command line tool
#RUN mkdir -p /urb/bin
#COPY urb-core/dist/urb-*-linux-x86_64/bin/linux-x86_64/redis-cli /urb/bin/
