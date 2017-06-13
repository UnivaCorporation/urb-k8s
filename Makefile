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


SUBDIRS=urb-core source/python

include urb-core/util/include.mk 

# 
dist:
	cd urb-core && make dist
	cd source/python && make dist

images:
	docker build --rm -t local/urb-service -f urb-service.dockerfile .
	docker build --rm -t local/urb-executor-runner -f urb-executor-runner.dockerfile .
	docker build --rm -t local/urb-redis -f redis.dockerfile .
	docker build --rm -t local/urb-cpp-framework -f cpp-framework.dockerfile .
	docker build --rm -t local/urb-python-framework -f python-framework.dockerfile .
#	cd source/docker && make images
