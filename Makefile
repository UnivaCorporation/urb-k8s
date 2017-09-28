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
PROJECT_ID=$(shell gcloud config get-value project 2> /dev/null)
REGISTRY=gcr.io
REPOSITORY=${REGISTRY}/${PROJECT_ID}

include urb-core/util/include.mk 

# 
dist:
	cd urb-core && make dist
	cd source/python && make dist

urb-service: urb-python-base
	docker build --rm -t local/urb-service -f urb-service.dockerfile .

urb-redis:
	cd source; docker build --rm -t local/urb-redis -f redis.dockerfile .

urb-executor-runner: urb-python-base
	docker build --rm -t local/urb-executor-runner -f urb-executor-runner.dockerfile .

cpp-framework: urb-bin-base
	cd test/example-frameworks; docker build --rm -t local/cpp-framework -f cpp-framework.dockerfile .

python-framework: urb-python-base
	docker build --rm -t local/python-framework -f python-framework.dockerfile .

python-executor-runner: urb-executor-runner
	docker build --rm -t local/python-executor-runner -f python-executor-runner.dockerfile .

urb-python-base: urb-bin-base
	docker build --rm -t local/urb-python-base -f urb-python-base.dockerfile .

urb-bin-base:
	docker build --rm -t local/urb-bin-base -f urb-bin-base.dockerfile .

images: urb-service urb-redis urb-executor-runner cpp-framework python-framework


gimages:
	docker build --rm -t ${REPOSITORY}/urb-service -f urb-service.dockerfile . && gcloud docker -- push ${REPOSITORY}/urb-service
	docker build --rm -t ${REPOSITORY}/urb-executor-runner -f urb-executor-runner.dockerfile . && gcloud docker -- push ${REPOSITORY}/urb-executor-runner
	docker build --rm -t ${REPOSITORY}/urb-redis -f redis.dockerfile . && gcloud docker -- push ${REPOSITORY}/urb-redis
	docker build --rm -t ${REPOSITORY}/urb-cpp-framework -f cpp-framework.dockerfile . && gcloud docker -- push ${REPOSITORY}/urb-cpp-framework
	docker build --rm -t ${REPOSITORY}/urb-python-framework -f python-framework.dockerfile . && gcloud docker -- push ${REPOSITORY}/urb-python-framework
#	docker build --rm -t ${REPOSITORY}/urb-pv -f urb-pv.dockerfile . && gcloud docker -- push ${REPOSITORY}/urb-pv
