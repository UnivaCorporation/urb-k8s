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

SUBDIRS=3rdparty

ifeq ($(shell uname -s),SunOS)
SETUP_ENV=PYCC_CC=gcc
endif

REDIS_BIN=../cpp/3rdparty/redis/build/redis-4.0.2/src

include ../../util/include.mk

all: build dist

# Stubs for default targets
.PHONY:deps install clean dist egg distclean test
deps install test:



urb/__init__.py : $(TOP)/util/params.mk
	echo "__version__ = '$(VERSION)'" > $@

mesos_version:
	$(SED) -Ei "s/^[ \t]*MESOS_VERSION[ \t]*=[ \t]['\"][0-9.]+['\"]/    MESOS_VERSION = `awk '/#define[ \t]+MESOS_VERSION/ { print $$3 }' $(TOP)/source/cpp/liburb/mesos/include/mesos/version.hpp`/" $(TOP)/source/python/urb/service/mesos_handler.py

distclean: tidy

build: urb/__init__.py mesos_version
	$(SETUP_ENV) $(PYTHON) setup.py build

dist: egg sdist

egg: urb/__init__.py
	$(SETUP_ENV) $(PYTHON) setup.py bdist_egg

sdist: urb/__init__.py
	$(SETUP_ENV) $(PYTHON) setup.py sdist

test: urb/__init__.py
	-qconf -djc TestFramework_`hostname`
	if [ "`$(REDIS_BIN)/redis-cli ping`" != "PONG" ]; then $(REDIS_BIN)/redis-server --protected-mode no& fi
	$(SETUP_ENV) URB_CONFIG_FILE=`pwd`/test/urb.conf $(PYTHON) setup.py nosetests -w test
	if [ "`$(REDIS_BIN)/redis-cli ping`" = "PONG" ]; then $(REDIS_BIN)/redis-cli flushdb; $(REDIS_BIN)/redis-cli shutdown; fi

clean:
	rm -rf build *.egg-info `find . -name '*.pyc'` urb/__init__.py

tidy: clean
	rm -rf dist

