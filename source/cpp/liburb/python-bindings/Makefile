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


#Python stuff
DIST_DIR=dist
VIRTUALENV=$(DIST_DIR)/testpy
PYTHONEGG=$(DIST_DIR)/mesos-$(EXT_MESOS_VERSION)-py$(EGG_PYV).egg
PYTHONEGG_SDIST=$(DIST_DIR)/mesos-$(EXT_MESOS_VERSION).tar.gz
PYTHONEGG_INTERFACE=$(DIST_DIR)/mesos.interface-$(EXT_MESOS_VERSION)-py$(EGG_PYV).egg
PYTHONEGG_INTERFACE_SDIST=$(DIST_DIR)/mesos.interface-$(EXT_MESOS_VERSION).tar.gz
PYTHONEGG_NATIVE=$(DIST_DIR)/mesos.native-$(EXT_MESOS_VERSION)-py$(EGG_PYV).egg
PYTHONEGG_NATIVE_SDIST=$(DIST_DIR)/mesos.native-$(EXT_MESOS_VERSION).tar.gz
PYTHONEGG_EXECUTOR=$(DIST_DIR)/mesos.executor-$(EXT_MESOS_VERSION)-py$(EGG_PYV)-$(EGG_ARCH).egg
PYTHONEGG_EXECUTOR_SDIST=$(DIST_DIR)/mesos.executor-$(EXT_MESOS_VERSION).tar.gz
PYTHONEGG_SCHEDULER=$(DIST_DIR)/mesos.scheduler-$(EXT_MESOS_VERSION)-py$(EGG_PYV)-$(EGG_ARCH).egg
PYTHONEGG_SCHEDULER_SDIST=$(DIST_DIR)/mesos.scheduler-$(EXT_MESOS_VERSION).tar.gz
URB_PYTHON_INCLUDES=../$(BUILDDIR)/python_bindings.mk
MESOS_PROTO_INC=../$(BUILDDIR)/include/mesos/mesos_pb2.py
MESOS_PROTO_TARGET=interface/src/mesos/interface/mesos_pb2.py
REDIS_BIN=../../3rdparty/redis/build/redis-4.0.2/src/

ifeq ($(STDCPP11),true)
  CFLAGS += -std=c++11 -std=c++1y
else
  CFLAGS += -std=c++0x
endif

ifeq ($(shell uname -s),SunOS)
  SETUP_ENV=PYCC_CC=gcc CFLAGS="$(CFLAGS)"
else
  SETUP_ENV=CFLAGS="$(CFLAGS)"
endif


.PHONY:all clean test env distclean deps install

include ../../../../util/include.mk
-include $(URB_PYTHON_INCLUDES)

ifeq ($(EGG_PYV),2.6)
  VENV_FLAGS = --system-site-packages --no-download
endif

#Include an built makefile that provides include and lib paths

# Build everthing
all: $(BUILDDIR) $(PYTHONEGG) $(PYTHONEGG_SDIST) \
    $(PYTHONEGG_INTERFACE) $(PYTHONEGG_INTERFACE_SDIST)\
    $(PYTHONEGG_NATIVE) $(PYTHONEGG_NATIVE_SDIST) \
    $(PYTHONEGG_EXECUTOR) $(PYTHONEGG_EXECUTOR_SDIST) \
    $(PYTHONEGG_SCHEDULER) $(PYTHONEGG_SCHEDULER_SDIST)

# Nothing to do
install:

# # Nothing to do
deps:

# Standard clean rules
clean:
	rm -f $(MESOS_PROTO_TARGET)
	rm -rf $(BUILDDIR)
	rm -rf interface/build
	rm -rf native/build
	rm -rf native_common/build
	rm -rf native/executor
	rm -rf native/scheduler
	rm -rf interface/src/mesos.interface.egg-info
	rm -rf native/src/mesos.native.egg-info
	rm -rf native_common/src/mesos.native.egg-info
	rm -rf executor/src/mesos.native.egg-info
	rm -rf scheduler/src/mesos.native.egg-info
	rm -rf src/mesos.egg-info

distclean: clean
	rm -rf $(DIST_DIR)

# Make the root build directory
$(BUILDDIR):
	echo "Make the root build directory: $@"
	mkdir -p $@

$(VIRTUALENV)/.built:
	virtualenv $(VENV_FLAGS) $(VIRTUALENV)
	touch $@

# There is a system limitation (BINPRM_BUF_SIZE = 128) for the lenth of the interpreter path in a
# header of the scripts so this line doesn't work (when calling 'easy_install') with long jenkins build path resulting with
# "bad interpreter: No such file or directory" error. So the workaround is to run easy_install directly:
# python /path/to/easy_install
$(VIRTUALENV)/.egg-installed: $(VIRTUALENV)/.built $(PYTHONEGG) $(PYTHONEGG_INTERFACE) $(PYTHONEGG_NATIVE) $(PYTHONEGG_SCHEDULER) $(PYTHONEGG_EXECUTOR)
	. $(VIRTUALENV)/bin/activate && python `which easy_install` $(PYTHONEGG_INTERFACE) $(PYTHONEGG_SCHEDULER) $(PYTHONEGG_EXECUTOR) $(PYTHONEGG_NATIVE)
	touch $@

$(MESOS_PROTO_TARGET) : $(MESOS_PROTO_INC)
	cp $^ $@


$(PYTHONEGG_SDIST): $(URB_PYTHON_INCLUDES)
	$(SETUP_ENV) $(PYTHON) setup.py sdist

$(PYTHONEGG): $(URB_PYTHON_INCLUDES)
	$(SETUP_ENV) $(PYTHON) setup.py bdist_egg

$(PYTHONEGG_INTERFACE_SDIST): $(MESOS_PROTO_TARGET) $(URB_PYTHON_INCLUDES)
	cd interface && $(SETUP_ENV) $(PYTHON) setup.py sdist --dist-dir=../dist

$(PYTHONEGG_INTERFACE): $(MESOS_PROTO_TARGET) $(URB_PYTHON_INCLUDES)
	cd interface && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../dist

$(PYTHONEGG_NATIVE_SDIST): $(URB_PYTHON_INCLUDES)
	cd native && $(SETUP_ENV) $(PYTHON) setup.py sdist --dist-dir=../dist

$(PYTHONEGG_NATIVE): $(URB_PYTHON_INCLUDES)
	cd native && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../dist

$(PYTHONEGG_EXECUTOR_SDIST): $(URB_PYTHON_INCLUDES)
	cd executor && $(SETUP_ENV) $(PYTHON) setup.py sdist --dist-dir=../dist

$(PYTHONEGG_EXECUTOR): $(URB_PYTHON_INCLUDES)
	cd executor && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../dist

$(PYTHONEGG_SCHEDULER_SDIST): $(URB_PYTHON_INCLUDES)
	cd scheduler && $(SETUP_ENV) $(PYTHON) setup.py sdist --dist-dir=../dist

$(PYTHONEGG_SCHEDULER): $(URB_PYTHON_INCLUDES)
	cd scheduler && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../dist

test: $(BUILDDIR) $(VIRTUALENV)/.egg-installed
	# Only run tests if a master broker is active
	( [ `$(REDIS_BIN)/redis-cli get urb.master` ] && . $(VIRTUALENV)/bin/activate && LD_LIBRARY_PATH=`pwd`/../build ./test/test_framework.py urb://localhost ) || echo "Skipping test since no URB master is registered."

env:
	@echo BUILDDIR=$(BUILDDIR)
	@echo BUILD_DIR=$(BUILD_DIR)
	@echo DIST_DIR=$(DIST_DIR)
	@echo PYTHONEGG=$(PYTHONEGG)
	@echo PYTHONEGG_INTERFACE=$(PYTHONEGG_INTERFACE)
	@echo PYTHONEGG_NATIVE=$(PYTHONEGG_NATIVE)
	@echo PYTHONEGG_NATIVE_COMMON=$(PYTHONEGG_NATIVE_COMMON)
	@echo PYTHONEGG_EXECUTOR=$(PYTHONEGG_EXECUTOR)
	@echo PYTHONEGG_SCHEDULER=$(PYTHONEGG_SCHEDULER)
	@echo EXT_MESOS_VERSION=$(EXT_MESOS_VERSION)
	@echo CFLAGS=$(CFLAGS)
	@echo VENV_FLAGS=$(VENV_FLAGS)
	@echo EGG_PYV=$(EGG_PYV)
