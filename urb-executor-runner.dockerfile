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

FROM local/urb-python-base

# install java
RUN yum update -y; yum install -y java-1.8.0-openjdk-headless python-pip; yum clean all

# install Python kubernetes client
RUN pip install kubernetes

# set environment variables required by URB executor runner and copy configuration file
#ENV URB_ROOT=/urb
RUN mkdir -p $URB_ROOT/etc
ENV URB_CONFIG_FILE=$URB_ROOT/etc/urb.executor_runner.conf
COPY etc/urb.executor_runner.conf $URB_ROOT/etc

# copy fetcher and command executor
RUN mkdir -p $URB_ROOT/bin
COPY urb-core/dist/urb-*-linux-x86_64/bin/linux-x86_64/fetcher \
     urb-core/dist/urb-*-linux-x86_64/bin/linux-x86_64/command-executor \
     $URB_ROOT/bin/

# Java home
ENV JAVA_HOME=/etc/alternatives/jre_openjdk

ENTRYPOINT ["/usr/bin/urb-executor-runner"]
