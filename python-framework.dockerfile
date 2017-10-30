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


# python example framework requires "test_framework.py" on framework side
# and custom executor "test_executor.py" on executor runner side
# (in python-executor-runner.dockerfile) to be located in the same path (/urb/bin)

FROM local/urb-python-base

RUN mkdir -p /urb/bin

COPY urb-core/dist/urb-*/share/examples/frameworks/python/test_framework.py /urb/bin/
ENTRYPOINT ["/urb/bin/test_framework.py", "urb://urb-master:6379"]


