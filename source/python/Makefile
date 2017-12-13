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

ifeq ($(shell uname -s),SunOS)
SETUP_ENV=PYCC_CC=gcc
endif

K8S_ADAPTER_INIT=k8s_adapter/__init__.py
REDIS_BIN=../../urb-core/source/cpp/3rdparty/redis/build/redis-4.0.2/src

include ../../urb-core/util/include.mk

all: build dist

# Stubs for default targets
.PHONY:deps install clean dist egg distclean test
deps install test:

$(K8S_ADAPTER_INIT) : $(TOP)/util/params.mk
	echo "__version__ = '$(VERSION)'" > $@

distclean: tidy

build: $(K8S_ADAPTER_INIT)
	$(SETUP_ENV) $(PYTHON) setup.py build

dist: egg sdist

egg: $(K8S_ADAPTER_INIT)
	$(SETUP_ENV) $(PYTHON) setup.py bdist_egg

sdist: $(K8S_ADAPTER_INIT)
	$(SETUP_ENV) $(PYTHON) setup.py sdist

test: $(K8S_ADAPTER_INIT)
	sudo pip install kubernetes
	if [ "$$($(REDIS_BIN)/redis-cli ping)" != "PONG" ]; then $(REDIS_BIN)/redis-server& fi
	$(SETUP_ENV) URB_CONFIG_FILE=$$(pwd)/test/urb.conf $(PYTHON) setup.py nosetests
	if [ "$$($(REDIS_BIN)/redis-cli ping)" == "PONG" ]; then echo -e "flushdb\nshutdown\nquit\n" | $(REDIS_BIN)/redis-cli; fi

clean:
	rm -rf build *.egg-info `find . -name '*.pyc'` $(K8S_ADAPTER_INIT)

tidy: clean
	rm -rf dist

