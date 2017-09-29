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
IMAGES=urb-service urb-executor-runner python-framework python-executor-runner urb-python-base urb-bin-base
GIMAGES=$(addprefix g-,$(IMAGES)) g-urb-redis g-cpp-framework
IMAGES-clean=$(addsuffix -clean,$(IMAGES)) urb-redis-clean cpp-framework-clean

.PHONY: $(IMAGES) urb-redis cpp-framework $(GIMAGES) $(IMAGES-clean)

PROJECT_ID=$(shell gcloud config get-value project 2> /dev/null)
REGISTRY=gcr.io
REPOSITORY=${REGISTRY}/${PROJECT_ID}

include urb-core/util/include.mk 

dist:
	cd urb-core && make dist
	cd source/python && make dist

$(IMAGES):
	docker build --rm -t local/$@ -f $@.dockerfile .

urb-service urb-executor-runner python-framework : urb-python-base

python-executor-runner: urb-executor-runner

urb-python-base: urb-bin-base

urb-redis:
	cd source; docker build --rm -t local/urb-redis -f urb-redis.dockerfile .

cpp-framework: urb-bin-base
	cd test/example-frameworks; docker build --rm -t local/cpp-framework -f cpp-framework.dockerfile .

images: $(IMAGES) urb-redis cpp-framework

$(GIMAGES):
	make $(subst g-,,$@)-clean
	im=$(subst g-,,$@); gim=${REPOSITORY}/$$im; docker tag local/$$im $$gim && gcloud docker -- push $$gim

gimages: $(GIMAGES)

$(IMAGES-clean):
	-im=${REPOSITORY}/$(subst -clean,,$(subst g-,,$@)); gcloud container images delete -q $$im; for hh in $$(gcloud compute instances list | awk '/gke/ {print $$1}'); do gcloud compute --project ${PROJECT_ID} ssh $$hh -- docker rmi -f $$im; done

echo:
	@echo "IMAGES: $(IMAGES)"
	@echo "GIMAGES: $(GIMAGES)"
	@echo "IMAGES-clean: $(IMAGES-clean)"
