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


ifndef TOP
ROOT            = $(dir $(filter %params.mk,$(MAKEFILE_LIST)))
ROOT            := $(ROOT:%/util/=%)
ROOT            := $(ROOT:util/=.)
export TOP             := $(shell cd $(ROOT) >/dev/null 2>&1 && echo $$PWD)
endif

export URB_REL_STR       = Development
export GIT_REV          := git$(shell git rev-parse --verify head)

# Setting the system environment variable URB_REL when running make
# will override the contents of the release string.
#
# ie:
#
# $ URB_REL="Universal Resource Broker v1.0" make
#
# By default the library will contain the string prepended with "GIT:"
# with URB_REL_STR variable content bellow.
ifneq ($(strip $(GIT_REV)),)
  export URB_REL_STR       = Version ($(GIT_REV))
endif

# URB Makefile parameters
export SHORT_NAME=urb
export NAME=lib$(SHORT_NAME)

export VERSION?=0.0.0
export SOVERSION=$(shell echo $(VERSION) | cut -d'.' -f 1)
export LIB_SONAME=$(NAME).so.$(SOVERSION)
export LIB_SOBIG=$(NAME)_big.so.$(SOVERSION)
export LIB_NAME=$(NAME).so.$(VERSION)
export LIB_BIG=$(NAME)_big.so.$(VERSION)
export LIB_NAME_SHORT=$(NAME).so
export LIB_BIG_SHORT=$(NAME)_big.so
export LIB_TARGET=$(BUILDDIR)/$(LIB_NAME)
export LIB_BIG_TARGET=$(BUILDDIR)/$(LIB_BIG)
export ARCHIVE_NAME=$(BUILDDIR)/$(NAME).a

export EXT_MESOS_VERSION?=$(shell awk -F'"' '/^\#define MESOS_VERSION / {print $$2}' $(TOP)/source/cpp/liburb/mesos/include/mesos/version.hpp)
STOCK_MESOS_DIR?=/opt/mesos
export EXT_MESOS_SRC_DIR=$(STOCK_MESOS_DIR)/mesos-$(EXT_MESOS_VERSION)

# Boost path
export BOOST_ROOT?=$(TOP)/source/cpp/3rdparty/boost/boost-1.58.0

ifeq ($(shell uname -s),SunOS)
  export PYTHON?=/usr/bin/python
  export FIND?=gfind
  export TAR?=gtar
  export PATCH?=gpatch
  export AR?=gar
  export SED?=gsed
else
  export PYTHON?=python
  export FIND?=find
  export TAR?=tar
  export PATCH?=patch
  export AR?=ar
  export SED?=sed
endif

export CMAKE?=cmake

# Java Variables
export JAVA_HOME?=/etc/alternatives/java_sdk

# python version and architecture used for eggs files name
#export EGG_PYOS?=$(shell python $(TOP)/source/installer/whatos/whatos.py)
export EGG_PYV=$(shell python -c "import sys;t='{v[0]}.{v[1]}'.format(v=list(sys.version_info[:2]));sys.stdout.write(t)")
ifeq ($(shell uname -s),SunOS)
  export EGG_ARCH=$(shell python -c "import platform; print(platform.platform(aliased=True, terse=True).lower() + '-' + platform.machine())")
else
  export EGG_ARCH=$(shell python -c "import platform; print(platform.system().lower() + '-' + platform.machine())")
endif

export GCCVERSION:=$(shell gcc -dumpversion | sed -e 's/\.\([0-9][0-9]\)/\1/g' -e 's/\.\([0-9]\)/0\1/g' -e 's/^[0-9]\{3,4\}$$/&00/')
export STDCPP11:=$(shell [ $(GCCVERSION) -ge 40700 ] && echo true)

