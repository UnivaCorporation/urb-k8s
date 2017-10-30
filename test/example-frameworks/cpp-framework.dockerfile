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

ENV URB_MASTER=urb://urb-master:6379
