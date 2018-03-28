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
PROTOBUF_ARCHIVE=$(shell ls protobuf-[0-9].*.tar.gz)
PROTOBUF_NAME=$(subst .tar.gz,,$(PROTOBUF_ARCHIVE))
PROTOBUF_EGG=$(PROTOBUF_NAME)-py$(EGG_PYV)-$(EGG_ARCH).egg
ARGPARSE_ARCHIVE=$(shell ls argparse-*.tar.gz)
ARGPARSE_NAME=$(subst .tar.gz,,$(ARGPARSE_ARCHIVE))
ARGPARSE_EGG=$(ARGPARSE_NAME)-py$(EGG_PYV)-$(EGG_ARCH).egg
GOOGLECOMMON_ARCHIVE=$(shell ls google-common-*.tar.gz)
GOOGLECOMMON_NAME=$(subst .tar.gz,,$(GOOGLECOMMON_ARCHIVE))
GOOGLECOMMON_EGG=$(GOOGLECOMMON_NAME)-py$(EGG_PYV).egg
INOTIFYX_ARCHIVE=$(shell ls inotifyx-*.tar.gz)
INOTIFYX_NAME=$(subst .tar.gz,,$(INOTIFYX_ARCHIVE))
INOTIFYX_EGG=$(INOTIFYX_NAME)-py$(EGG_PYV)-$(EGG_ARCH).egg
GEVENTINOTIFYX_ARCHIVE=$(shell ls gevent_inotifyx-*.tar.gz)
GEVENTINOTIFYX_NAME=$(subst .tar.gz,,$(GEVENTINOTIFYX_ARCHIVE))
GEVENTINOTIFYX_EGG=$(GEVENTINOTIFYX_NAME)-py$(EGG_PYV).egg
FLASK_ARCHIVE=$(shell ls Flask-*.tar.gz)
FLASK_NAME=$(subst .tar.gz,,$(FLASK_ARCHIVE))
FLASK_EGG=$(FLASK_NAME)-py$(EGG_PYV).egg
MARKUPSAFE_ARCHIVE=$(shell ls MarkupSafe-*.tar.gz)
MARKUPSAFE_NAME=$(subst .tar.gz,,$(MARKUPSAFE_ARCHIVE))
MARKUPSAFE_EGG=$(MARKUPSAFE_NAME)-py$(EGG_PYV)-$(EGG_ARCH).egg
ITSDANGEROUS_ARCHIVE=$(shell ls itsdangerous-*.tar.gz)
ITSDANGEROUS_NAME=$(subst .tar.gz,,$(ITSDANGEROUS_ARCHIVE))
ITSDANGEROUS_EGG=$(ITSDANGEROUS_NAME)-py$(EGG_PYV).egg

DIST_EGGS=$(DIST_DIR)/$(GEVENT_EGG) \
          $(DIST_DIR)/$(GREENLET_EGG) \
          $(DIST_DIR)/$(SORTEDCONTAINERS_EGG) \
          $(DIST_DIR)/$(VIRTUALENV_EGG) \
          $(DIST_DIR)/$(XMLTODICT_EGG) \
          $(DIST_DIR)/$(PYMONGO_EGG) \
          $(DIST_DIR)/$(PROTOBUF_EGG) \
          $(DIST_DIR)/$(ARGPARSE_EGG) \
          $(DIST_DIR)/$(REDIS_EGG) \
          $(DIST_DIR)/$(GOOGLECOMMON_EGG) \
          $(DIST_DIR)/$(FLASK_EGG) \
          $(DIST_DIR)/$(MARKUPSAFE_EGG) \
          $(DIST_DIR)/$(ITSDANGEROUS_EGG)

# some packages can be used directly as prebuild eggs or wheels
SIX_ARCHIVE=$(shell ls six-*.whl)
WERKZEUG_ARCHIVE=$(shell ls Werkzeug-*.whl)
JINJA2_ARCHIVE=$(shell ls Jinja2-*.whl)
CLICK_ARCHIVE=$(shell ls click-*.whl)

DIST_PREBUILT=$(DIST_DIR)/$(SIX_ARCHIVE) \
              $(DIST_DIR)/$(WERKZEUG_ARCHIVE) \
              $(DIST_DIR)/$(JINJA2_ARCHIVE) \
              $(DIST_DIR)/$(CLICK_ARCHIVE)

ifeq ($(shell uname -s),SunOS)
  SETUP_ENV=PYCC_CC=gcc
else
  DIST_EGGS+=$(DIST_DIR)/$(INOTIFYX_EGG) $(DIST_DIR)/$(GEVENTINOTIFYX_EGG)
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

# protobuf 3.0.0 has incorrect egg-info files permissions
$(DIST_DIR)/$(PROTOBUF_EGG): $(PROTOBUF_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	chmod go+r $(BUILDDIR)/$(PROTOBUF_NAME)/protobuf.egg-info/*
	cd $(BUILDDIR)/$(PROTOBUF_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(ARGPARSE_EGG): $(ARGPARSE_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	cd $(BUILDDIR)/$(ARGPARSE_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(GOOGLECOMMON_EGG): $(GOOGLECOMMON_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	cd $(BUILDDIR)/$(GOOGLECOMMON_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(INOTIFYX_EGG): $(INOTIFYX_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	cd $(BUILDDIR); $(PATCH) -p1 < ../$(INOTIFYX_NAME).patch
	cd $(BUILDDIR)/$(INOTIFYX_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(GEVENTINOTIFYX_EGG): $(GEVENTINOTIFYX_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	cd $(BUILDDIR); $(PATCH) -p1 < ../$(GEVENTINOTIFYX_NAME).patch
	cd $(BUILDDIR)/$(GEVENTINOTIFYX_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(FLASK_EGG): $(FLASK_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	cd $(BUILDDIR)/$(FLASK_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(MARKUPSAFE_EGG): $(MARKUPSAFE_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	cd $(BUILDDIR)/$(MARKUPSAFE_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(ITSDANGEROUS_EGG): $(ITSDANGEROUS_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	cd $(BUILDDIR)/$(ITSDANGEROUS_NAME) && $(SETUP_ENV) $(PYTHON) setup.py bdist_egg --dist-dir=../../$(DIST_DIR)

$(DIST_DIR)/$(SIX_ARCHIVE): $(SIX_ARCHIVE)
	cp $< $(DIST_DIR)

$(DIST_DIR)/$(WERKZEUG_ARCHIVE): $(WERKZEUG_ARCHIVE)
	cp $< $(DIST_DIR)

$(DIST_DIR)/$(JINJA2_ARCHIVE): $(JINJA2_ARCHIVE)
	cp $< $(DIST_DIR)

$(DIST_DIR)/$(CLICK_ARCHIVE): $(CLICK_ARCHIVE)
	cp $< $(DIST_DIR)

dist: $(BUILDDIR)/.dummy $(DIST_DIR)/.dummy $(DIST_EGGS) $(DIST_PREBUILT)

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
	@echo SIX_ARCHIVE=$(SIX_ARCHIVE)
	@echo DIST_PREBUILT=$(DIST_PREBUILT)
