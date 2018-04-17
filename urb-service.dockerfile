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

RUN pip install kubernetes

# copy k8s adapter Python egg
COPY source/python/dist/k8s_adapter-*-py2.7.egg /tmp/

# install URB and k8s adapter
RUN easy_install /tmp/k8s_adapter-*-py2.7.egg

# set environment variables required by URB service and copy configuration files
#ENV URB_ROOT=/urb
#ENV URB_CONFIG_FILE=$URB_ROOT/etc/urb.conf
#RUN mkdir -p $URB_ROOT/etc
#COPY etc/urb.conf etc/urb.executor_runner.conf $URB_ROOT/etc/
EXPOSE 6379 5060 5061

ENTRYPOINT ["/usr/bin/urb-service"]
