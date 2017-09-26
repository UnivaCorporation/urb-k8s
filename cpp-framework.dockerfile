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


# C++ example framework is based on urb-bin-base image and relies on
# framework (example_framework.test) and custom executor (example_executor.test)
# executables to be located on persistent volume example-pv.
# it only requires environment variable URB_MASTER to be set here

FROM local/urb-bin-base

ENV URB_MASTER=urb://urb-master.default:6379

#RUN mkdir -p /urb/bin
#COPY urb-core/dist/urb-*-linux-x86_64/share/examples/frameworks/linux-x86_64/example_*.test /urb/bin/
#RUN mkdir -p /opt/bin
#COPY urb-core/dist/urb-*-linux-x86_64/share/examples/frameworks/linux-x86_64/example_*.test /opt/bin/

# for testing purposes add redis command line tool
#COPY urb-core/dist/urb-*-linux-x86_64/bin/linux-x86_64/redis-cli /urb/bin/

#ENTRYPOINT ["/urb/bin/example_framework.test"]
#ENTRYPOINT ["/opt/bin/example_framework.test"]
#ENTRYPOINT ["/opt/urb/bin/example_framework.test"]
