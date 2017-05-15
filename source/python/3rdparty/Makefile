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

default: dist

# Stubs for default targets
.PHONY:deps install clean dist egg distclean test env 3rdparty-test
deps install test:

include ../../../util/include.mk

DIST_DIR=dist

GREENLET_ARCHIVE=$(shell ls greenlet-*.zip)
GREENLET_NAME=$(subst .zip,,$(GREENLET_ARCHIVE))
GREENLET_EGG=$(GREENLET_NAME)-py$(EGG_PYV)-$(EGG_ARCH).egg
GEVENT_ARCHIVE=$(shell ls gevent-*.tar.gz)
GEVENT_NAME=$(subst .tar.gz,,$(GEVENT_ARCHIVE))
GEVENT_EGG=$(GEVENT_NAME)-py$(EGG_PYV)-$(EGG_ARCH).egg
REDIS_ARCHIVE=$(shell ls redis-*.tar.gz)
REDIS_NAME=$(subst .tar.gz,,$(REDIS_ARCHIVE))
REDIS_EGG=$(REDIS_NAME)-py$(EGG_PYV).egg
SORTEDCONTAINERS_ARCHIVE=$(shell ls sortedcontainers-*.tar.gz)
SORTEDCONTAINERS_NAME=$(subst .tar.gz,,$(SORTEDCONTAINERS_ARCHIVE))
SORTEDCONTAINERS_EGG=$(SORTEDCONTAINERS_NAME)-py$(EGG_PYV).egg
VIRTUALENV_ARCHIVE=$(shell ls virtualenv-*.tar.gz)
VIRTUALENV_NAME=$(subst .tar.gz,,$(VIRTUALENV_ARCHIVE))
VIRTUALENV_EGG=$(VIRTUALENV_NAME)-py$(EGG_PYV).egg
XMLTODICT_ARCHIVE=$(shell ls xmltodict-*.tar.gz)
XMLTODICT_NAME=$(subst .tar.gz,,$(XMLTODICT_ARCHIVE))
XMLTODICT_EGG=$(XMLTODICT_NAME)-py$(EGG_PYV).egg
PYMONGO_ARCHIVE=$(shell ls pymongo-*.tar.gz)
PYMONGO_NAME=$(subst .tar.gz,,$(PYMONGO_ARCHIVE))
PYMONGO_EGG=$(PYMONGO_NAME)-py$(EGG_PYV)-$(EGG_ARCH).egg
PROTOBUF_ARCHIVE=$(shell ls protobuf-*.tar.gz)
PROTOBUF_NAME=$(subst .tar.gz,,$(PROTOBUF_ARCHIVE))
PROTOBUF_EGG=$(PROTOBUF_NAME)-py$(EGG_PYV)-$(EGG_ARCH).egg
ARGPARSE_ARCHIVE=$(shell ls argparse-*.tar.gz)
ARGPARSE_NAME=$(subst .tar.gz,,$(ARGPARSE_ARCHIVE))
ARGPARSE_EGG=$(ARGPARSE_NAME)-py$(EGG_PYV)-$(EGG_ARCH).egg
GOOGLECOMMON_ARCHIVE=$(shell ls google-common-*.tar.gz)
GOOGLECOMMON_NAME=$(subst .tar.gz,,$(GOOGLECOMMON_ARCHIVE))
GOOGLECOMMON_EGG=$(GOOGLECOMMON_NAME)-py$(EGG_PYV).egg

DIST_EGGS=$(DIST_DIR)/$(GEVENT_EGG) \
          $(DIST_DIR)/$(GREENLET_EGG) \
          $(DIST_DIR)/$(SORTEDCONTAINERS_EGG) \
          $(DIST_DIR)/$(VIRTUALENV_EGG) \
          $(DIST_DIR)/$(XMLTODICT_EGG) \
          $(DIST_DIR)/$(PYMONGO_EGG) \
          $(DIST_DIR)/$(PROTOBUF_EGG) \
          $(DIST_DIR)/$(ARGPARSE_EGG) \
          $(DIST_DIR)/$(REDIS_EGG) \
          $(DIST_DIR)/$(GOOGLECOMMON_EGG)

ifeq ($(shell uname -s),SunOS)
SETUP_ENV=PYCC_CC=gcc
endif

distclean: clean

$(DIST_DIR)/.dummy: 
	mkdir -p $(DIST_DIR)
	touch $@

$(BUILDDIR)/.dummy: 
	mkdir -p $(BUILDDIR)
	touch $@

# Solaris 10 uses old /bin/sh which doesn't propagate OLDPWD env var to the child
# so we need to patch setup.py to use /bin/bash instead (it also doesn't
# support $(cmd) notation so `cmd` has to be used and double equal sign)
$(DIST_DIR)/$(GEVENT_EGG): $(GEVENT_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	if [ "`uname -sr`" = "SunOS 5.10" ]; then sed 's/return check_call(cmd, shell=True)/return check_call(cmd, shell=True, executable="\/bin\/bash")/' $(BUILDDIR)/$(GEVENT_NAME)/setup.py > /tmp/setup.py; mv /tmp/setup.py $(BUILDDIR)/$(GEVENT_NAME)/setup.py; fi
	cd $(BUILDDIR)/$(GEVENT_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(GREENLET_EGG): $(GREENLET_ARCHIVE)
	cd $(BUILDDIR) && unzip ../$<
	cd $(BUILDDIR)/$(GREENLET_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(REDIS_EGG): $(REDIS_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	cd $(BUILDDIR)/$(REDIS_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(SORTEDCONTAINERS_EGG): $(SORTEDCONTAINERS_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	cd $(BUILDDIR)/$(SORTEDCONTAINERS_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(VIRTUALENV_EGG): $(VIRTUALENV_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	cd $(BUILDDIR)/$(VIRTUALENV_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(XMLTODICT_EGG): $(XMLTODICT_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	cd $(BUILDDIR)/$(XMLTODICT_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(PYMONGO_EGG): $(PYMONGO_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	cd $(BUILDDIR)/$(PYMONGO_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(PROTOBUF_EGG): $(PROTOBUF_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	cd $(BUILDDIR)/$(PROTOBUF_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(ARGPARSE_EGG): $(ARGPARSE_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	cd $(BUILDDIR)/$(ARGPARSE_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(GOOGLECOMMON_EGG): $(GOOGLECOMMON_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	cd $(BUILDDIR)/$(GOOGLECOMMON_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

dist: $(BUILDDIR)/.dummy $(DIST_DIR)/.dummy $(DIST_EGGS)

test:
	@echo "Skipping recursive test of thirdparty eggs."
	@echo "Tests can be run with 'make 3rdparty-test' from this directory"

3rdparty-test: $(DIST_EGGS)
	cd $(BUILDDIR)/$(GEVENT_NAME) && $(PYTHON) setup.py test
	cd $(BUILDDIR)/$(GREENLET_NAME) && $(PYTHON) setup.py test
	cd $(BUILDDIR)/$(VIRTUALENV_NAME) && $(PYTHON) setup.py test
	cd $(BUILDDIR)/$(REDIS_NAME) && $(PYTHON) setup.py test

clean:
	rm -rf $(BUILDDIR) $(DIST_DIR)

env:
	@echo GEVENT_NAME=$(GEVENT_NAME)
	@echo GEVENT_ARCHIVE=$(GEVENT_ARCHIVE)
	@echo GREENLET_NAME=$(GREENLET_NAME)
	@echo GREENLET_ARCHIVE=$(GREENLET_ARCHIVE)
	@echo REDIS_NAME=$(REDIS_NAME)
	@echo REDIS_ARCHIVE=$(REDIS_ARCHIVE)
	@echo SORTEDCONTAINERS_NAME=$(SORTEDCONTAINERS_NAME)
	@echo SORTEDCONTAINERS_ARCHIVE=$(SORTEDCONTAINERS_ARCHIVE)
	@echo XMLTODICT_NAME=$(XMLTODICT_NAME)
	@echo XMLTODICT_ARCHIVE=$(XMLTODICT_ARCHIVE)
	@echo DIST_EGGS=$(DIST_EGGS)
