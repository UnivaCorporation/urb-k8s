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


SUBDIRS=source
FILTER_GOALS=dist
SHELL:=$(shell which bash)

include util/include.mk

# Python environment stuff
PY?=python
PYVERS=$(shell PATH=$(PYENV_HOME)/bin:$(PATH) $(PY) -c "from sys import version_info as v; print 'py'+str(v[0])+'.'+str(v[1])")
PYPLATFORM=$(shell PATH=$(PYENV_HOME)/bin:$(PATH) $(PY) -c "from distutils.util import get_platform; print get_platform()")
PYOS?=$(shell PATH=$(PYENV_HOME)/bin:$(PATH) $(PY) $(WHATOS_SRC)/$(WHATOS))
PLATFORMSTR=$(PYVERS)-$(PYOS)-$(PYPLATFORM)
DIST_DIR_NAME=$(SHORT_NAME)-$(VERSION)
DIST_URB_CORE_NAME=$(SHORT_NAME)-core-$(VERSION)
DEP_ARCH=$(DIST_DIR_NAME)-$(PLATFORMSTR)
GENERIC_SUFFIX:=$(shell $(PY) -c "import sys; l='l64' if 'lib64/python' in ' '.join(sys.path) else 'l32'; print l")
DEP_ARCH_GENERIC=$(DIST_DIR_NAME)-$(PYVERS)-generic-$(GENERIC_SUFFIX)-$(PYPLATFORM)
DEP_NOARCH=$(DIST_DIR_NAME)-$(PYVERS)
DEP_ARCH_BIN=$(DIST_DIR_NAME)-$(PYPLATFORM)
DEP_SDIST=$(DIST_DIR_NAME)-sdist
DIST_NAME_ARCH=$(DEP_ARCH).tar.gz
DIST_NAME_ARCH_GENERIC=$(DEP_ARCH_GENERIC).tar.gz
DIST_NAME_NOARCH=$(DEP_NOARCH).tar.gz
DIST_NAME_ARCH_BIN=$(DEP_ARCH_BIN).tar.gz
DIST_NAME_SDIST=$(DEP_SDIST).tar.gz

BASE_DIR=$(TOP)/dist
DIST_DIR=$(BASE_DIR)/$(DIST_DIR_NAME)
DIST_NAME_COMMON=$(DIST_URB_CORE_NAME).tar.gz
DIST_TARGET_COMMON=$(DIST_DIR)/../$(DIST_NAME_COMMON)
DIST_TARGET_ARCH=$(DIST_DIR)/pkg/$(DIST_NAME_ARCH)
DIST_TARGET_ARCH_GENERIC=$(DIST_DIR)/pkg/$(DIST_NAME_ARCH_GENERIC)
DIST_TARGET_NOARCH=$(DIST_DIR)/pkg/$(DIST_NAME_NOARCH)
DIST_TARGET_ARCH_BIN=$(DIST_DIR)/pkg/$(DIST_NAME_ARCH_BIN)
DIST_TARGET_SDIST=$(DIST_DIR)/pkg/$(DIST_NAME_SDIST)
DIST_TARGET_3RDPARTY_LICENSES=$(BASE_DIR)/3rdparty_licenses
DIST_TARGET_3RDPARTY_LICENSES_CPP=$(DIST_TARGET_3RDPARTY_LICENSES)/cpp
DIST_TARGET_3RDPARTY_LICENSES_PYTHON=$(DIST_TARGET_3RDPARTY_LICENSES)/python
DIST_TARGET_3RDPARTY_LICENSES_README=$(DIST_TARGET_3RDPARTY_LICENSES)/README

# Liburb stuff
LIBURB_DIR=source/cpp/liburb
LIBURB_TARGET_DIR=$(BASE_DIR)/$(DEP_ARCH_BIN)/lib/$(PYPLATFORM)
LIBURB_TARGET=$(LIBURB_TARGET_DIR)/$(LIB_NAME)
ifneq ($(shell uname -s),SunOS)
ifdef FULL_MESOS_LIB
LIBURB_BIG_TARGET=$(LIBURB_TARGET_DIR)/$(LIB_BIG)
endif
endif
LIBURB_PYTHON_BINDINGS_DIR=$(LIBURB_DIR)/python-bindings
LIBURB_PYTHON_ARCH_BINDINGS=$(LIBURB_PYTHON_BINDINGS_DIR)/dist/mesos.scheduler-$(EXT_MESOS_VERSION)-py$(EGG_PYV)-$(EGG_ARCH).egg \
                            $(LIBURB_PYTHON_BINDINGS_DIR)/dist/mesos.executor-$(EXT_MESOS_VERSION)-py$(EGG_PYV)-$(EGG_ARCH).egg
LIBURB_PYTHON_NOARCH_BINDINGS=$(LIBURB_PYTHON_BINDINGS_DIR)/dist/mesos.interface-$(EXT_MESOS_VERSION)-py$(EGG_PYV).egg \
                       $(LIBURB_PYTHON_BINDINGS_DIR)/dist/mesos.native-$(EXT_MESOS_VERSION)-py$(EGG_PYV).egg \
                       $(LIBURB_PYTHON_BINDINGS_DIR)/dist/mesos-$(EXT_MESOS_VERSION)-py$(EGG_PYV).egg
FETCHER_SRC=$(LIBURB_DIR)/$(BUILDDIR)/fetcher
FETCHER_TARGET=$(BASE_DIR)/$(DEP_ARCH_BIN)/bin/$(PYPLATFORM)
COMMAND_EXECUTOR_SRC=$(LIBURB_DIR)/build/command_executor.test
COMMAND_EXECUTOR_TARGET=$(BASE_DIR)/$(DEP_ARCH_BIN)/bin/$(PYPLATFORM)/command-executor

# Example
EXAMPLE_FRAMEWORK=$(LIBURB_DIR)/$(BUILDDIR)/example_framework.test \
                  $(LIBURB_DIR)/$(BUILDDIR)/example_executor.test \
                  $(LIBURB_DIR)/$(BUILDDIR)/long_lived_framework.test \
                  $(LIBURB_DIR)/$(BUILDDIR)/long_lived_executor.test \
                  $(LIBURB_DIR)/$(BUILDDIR)/docker_no_executor_framework.test
EXAMPLE_FRAMEWORK_TARGET=$(BASE_DIR)/$(DEP_ARCH_BIN)/share/examples/frameworks/$(PYPLATFORM)
EXAMPLE_PYTHON_FRAMEWORK=$(LIBURB_PYTHON_BINDINGS_DIR)/test/test_framework.py \
                         $(LIBURB_PYTHON_BINDINGS_DIR)/test/test_executor.py
EXAMPLE_PYTHON_FRAMEWORK_TARGET=$(DIST_DIR)/share/examples/frameworks/python

# Dev stuff
SHARE_INCLUDE_TARGET=$(DIST_DIR)/share/include
SHARE_INCLUDE_SRC=$(LIBURB_DIR)/$(BUILDDIR)/bindings_include

# Python stuff
URB_EGG_DIR=source/python
URB_EGG_NAME=$(SHORT_NAME)-$(VERSION)-$(PYVERS).egg
URB_SDIST_NAME=$(SHORT_NAME)-$(VERSION).tar.gz
EGG_DIR_ARCH=$(BASE_DIR)/$(DEP_ARCH)
EGG_DIR_NOARCH=$(BASE_DIR)/$(DEP_NOARCH)
SDIST_DIR=$(BASE_DIR)/$(DEP_SDIST)
URB_EGG_TARGET=$(DIST_DIR)/pkg/$(URB_EGG_NAME)
SDIST_THIRDPARTY_SRC=$(URB_EGG_DIR)/3rdparty
SDIST_BINDINGS_SRC=$(LIBURB_PYTHON_BINDINGS_DIR)/dist
THIRDPARTY_EGG_DIR=$(SDIST_THIRDPARTY_SRC)/dist

# Config files
CONFIG_DIR=etc
CONFIG_FILES=$(CONFIG_DIR)
CONFIG_FILE_TARGET=$(DIST_DIR)/etc

INSTALLER_TARGET=$(DIST_DIR)
WHATOS=whatos.py
TOOLS_DIR=tools
WHATOS_SRC=$(TOOLS_DIR)
WHATOS_TARGET=$(DIST_DIR)/bin

# Redis
REDIS_BIN_SRC=source/cpp/3rdparty/redis/dist/bin
REDIS_BIN_TARGET=$(BASE_DIR)/$(DEP_ARCH_BIN)/bin/$(PYPLATFORM)
REDIS_UTIL_SRC=source/cpp/3rdparty/redis/dist/utils
REDIS_UTIL_TARGET=$(DIST_DIR)/share/redis/utils
REDIS_DEFAULT_CONF_SRC=source/cpp/3rdparty/redis/dist/redis.conf
REDIS_DEFAULT_CONF_TARGET=$(DIST_DIR)/share/redis


.PHONY:dist
dist: $(DIST_TARGET_COMMON)

$(DIST_TARGET_ARCH_BIN): all $(DIST_DIR)/../.dummy $(LIBURB_TARGET) $(LIBURB_BIG_TARGET)
	mkdir -p $(@D)
	cp -f $(EXAMPLE_FRAMEWORK) $(EXAMPLE_FRAMEWORK_TARGET)
	cp $(REDIS_BIN_SRC)/* $(REDIS_BIN_TARGET)
	cp $(FETCHER_SRC) $(FETCHER_TARGET)
	cp $(COMMAND_EXECUTOR_SRC) $(COMMAND_EXECUTOR_TARGET)
	cd $(LIBURB_TARGET_DIR) && ln -sf $(LIB_NAME) $(LIB_SONAME) && ln -sf $(LIB_NAME) $(LIB_NAME_SHORT)
	cd $(LIBURB_TARGET_DIR) && ln -sf $(LIB_BIG) $(LIB_SOBIG) && ln -sf $(LIB_BIG) $(LIB_BIG_SHORT)
	cd $(BASE_DIR)/$(DEP_ARCH_BIN) && $(TAR) czvf $@ .

$(DIST_TARGET_NOARCH): all $(DIST_DIR)/../.dummy $(URB_EGG_TARGET) $(LIBURB_PYTHON_NOARCH_BINDINGS)
	mkdir -p $(@D)
	cp -f $(THIRDPARTY_EGG_DIR)/*$(PYVERS).egg $(EGG_DIR_NOARCH)
	cp -f $(LIBURB_PYTHON_NOARCH_BINDINGS) $(EGG_DIR_NOARCH)
	cd $(BASE_DIR)/$(DEP_NOARCH) && $(TAR) czvf $@ .

$(DIST_TARGET_ARCH): all $(DIST_DIR)/../.dummy $(URB_EGG_TARGET) $(LIBURB_PYTHON_ARCH_BINDINGS) 
	mkdir -p $(@D)
	cp -f $(THIRDPARTY_EGG_DIR)/*$(EGG_ARCH)* $(EGG_DIR_ARCH)
	cp $(LIBURB_PYTHON_ARCH_BINDINGS) $(EGG_DIR_ARCH)
	cd $(BASE_DIR)/$(DEP_ARCH) && $(TAR) czvf $@ .
	cp $(DIST_TARGET_ARCH) $(DIST_TARGET_ARCH_GENERIC)

$(DIST_TARGET_SDIST): all $(DIST_DIR)/../.dummy $(URB_EGG_DIR)/dist/$(URB_SDIST_NAME) $(LIBURB_PYTHON_ARCH_BINDINGS) 
	mkdir -p $(@D)
	$(TAR) xzvf $(URB_EGG_DIR)/dist/$(URB_SDIST_NAME) -C $(SDIST_DIR)
	$(TAR) xzvf $(SDIST_BINDINGS_SRC)/mesos-*.tar.gz -C $(SDIST_DIR)
	$(TAR) xzvf $(SDIST_BINDINGS_SRC)/mesos.interface-*.tar.gz -C $(SDIST_DIR)
	$(TAR) xzvf $(SDIST_BINDINGS_SRC)/mesos.native-*.tar.gz -C $(SDIST_DIR)
	$(TAR) xzvf $(SDIST_BINDINGS_SRC)/mesos.scheduler-*.tar.gz -C $(SDIST_DIR)
	$(TAR) xzvf $(SDIST_BINDINGS_SRC)/mesos.executor-*.tar.gz -C $(SDIST_DIR)
	cd $(SDIST_DIR) && $(TAR) czvf $@ .
	#cp $(URB_EGG_DIR)/dist/$(URB_SDIST_NAME) $@

$(DIST_TARGET_3RDPARTY_LICENSES_CPP): all $(DIST_DIR)/../.dummy $(LIBURB_TARGET)
	mkdir -p $@
	for lic_path in $$(find source/cpp/3rdparty \( -name COPYING -o -name COPYING\.txt -o \
	                                               -name LICENSE -o -name LICENSE\.txt -o \
	                                               -name AUTHORS -o -name AUTHORS\.txt \) -print); \
	do \
	  new_dir=$$(basename $$(dirname $$lic_path)); \
	  mkdir -p $@/$$new_dir; \
	  cp $$lic_path $@/$$new_dir; \
	  find $$(dirname $$lic_path) \( -name \*\.cpp -o -name \*\.h -o -name \*\.hpp \) -exec grep "Copyright ([cC])" {} \; | sed "s|^.*Copyright ([cC])|Copyright (c)|" | sort -u > $@/$$new_dir/COPYRIGHT; \
	  [ -s $@/$$new_dir/COPYRIGHT ] || rm $@/$$new_dir/COPYRIGHT; \
	done
	mkdir -p $@/mesos
	cp source/cpp/liburb/mesos/LICENSE $@/mesos
	cp source/cpp/liburb/mesos/NOTICE $@/mesos

$(DIST_TARGET_3RDPARTY_LICENSES_PYTHON): all $(DIST_DIR)/../.dummy $(LIBURB_TARGET)
	mkdir -p $@
	for lic_path in $$(find source/python/3rdparty \( -name COPYING -o -name COPYING\.txt -o \
	                                                  -name LICENSE -o -name LICENSE\.txt -o \
	                                                  -name AUTHORS -o -name AUTHORS\.txt \) -print); \
	do \
	  new_dir=$$(basename $$(dirname $$lic_path)); \
	  mkdir -p $@/$$new_dir; \
	  cp $$lic_path $@/$$new_dir; \
	  find $$(dirname $$lic_path) -name \*\.py -exec grep "Copyright" {} \; | sed "s|^.*Copyright|Copyright|" | sort -u > $@/$$new_dir/COPYRIGHT; \
	  [ -s $@/$$new_dir/COPYRIGHT ] || rm $@/$$new_dir/COPYRIGHT; \
	done

$(DIST_TARGET_3RDPARTY_LICENSES_README): $(DIST_TARGET_3RDPARTY_LICENSES_CPP) $(DIST_TARGET_3RDPARTY_LICENSES_PYTHON)
	mkdir -p $$(dirname $@)
	echo "The files in this directory hierarchy reference all third party components and" > $@
	echo "software modules which are used by the Universal Resource Broker product with" >> $@
	echo "applicable authorship, copyright statements and licenses. Please refer to the" >> $@
	echo "corresponding files for details." >> $@

$(DIST_TARGET_COMMON): all $(DIST_DIR)/../.dummy \
                       $(DIST_TARGET_ARCH) $(DIST_TARGET_NOARCH) $(DIST_TARGET_ARCH_BIN) $(DIST_TARGET_SDIST) \
                       $(DIST_TARGET_3RDPARTY_LICENSES_CPP) $(DIST_TARGET_3RDPARTY_LICENSES_PYTHON) \
                       $(DIST_TARGET_3RDPARTY_LICENSES_README)
#	cp -f -r $(CONFIG_FILES)/* $(CONFIG_FILE_TARGET)
	cp -f $(EXAMPLE_PYTHON_FRAMEWORK) $(EXAMPLE_PYTHON_FRAMEWORK_TARGET)
	cp -r $(DIST_TARGET_3RDPARTY_LICENSES) $(INSTALLER_TARGET)
	cp $(REDIS_UTIL_SRC)/*.* $(REDIS_UTIL_TARGET)
	cp $(REDIS_DEFAULT_CONF_SRC) $(REDIS_DEFAULT_CONF_TARGET)
	cp $(WHATOS_SRC)/*.* $(WHATOS_TARGET)
	rsync -av $(SHARE_INCLUDE_SRC)/ $(SHARE_INCLUDE_TARGET)/
	# Create a list of all of the files in the target directory and store for uninstallation
	touch $(DIST_DIR)/pkg/file-list.txt
	cd $(DIST_DIR) && find . | sort > $(DIST_DIR)/pkg/file-list.txt
	# Add .inst_logs so we don't delete logs during 'removeall' operation
	# Tar Gzip it all up
	cd $(DIST_DIR)/.. && $(TAR) czvf $@ $(DIST_DIR_NAME)
	# This will make dist always rebuild
	rm -f $(DIST_DIR)/../.dummy

# Make all of the dist directories
$(DIST_DIR)/../.dummy:
	rm -rf $(DIST_DIR)
	rm -rf $(BASE_DIR)/$(DEP_NOARCH)
	rm -rf $(BASE_DIR)/$(DEP_ARCH)
	rm -rf $(BASE_DIR)/$(DEP_ARCH_BIN)
	rm -rf $(BASE_DIR)/$(DEP_SDIST)
	mkdir -p $(BASE_DIR)/$(DEP_SDIST)
	mkdir -p $(LIBURB_TARGET_DIR)
	mkdir -p $(FETCHER_TARGET)
	mkdir -p $(EXAMPLE_FRAMEWORK_TARGET)
	mkdir -p $(DIST_DIR)
	mkdir -p $(DIST_DIR)/bin
	mkdir -p $(DIST_DIR)/etc
	mkdir -p $(DIST_DIR)/var/log
	mkdir -p $(EGG_DIR_ARCH)
	mkdir -p $(EGG_DIR_NOARCH)
	mkdir -p $(DIST_DIR)/dep/virtualenv
	mkdir -p $(DIST_DIR)/share
	mkdir -p $(DIST_DIR)/share/doc
	mkdir -p $(DIST_DIR)/share/doc/examples
	mkdir -p $(DIST_DIR)/share/examples/frameworks/python
	mkdir -p $(DIST_DIR)/share/examples/templates
	mkdir -p $(DIST_DIR)/share/redis/utils
	mkdir -p $(SHARE_INCLUDE_TARGET)
	touch $@

$(LIBURB_TARGET): $(LIBURB_DIR)/$(LIB_TARGET)
	cp -f $< $@

ifdef FULL_MESOS_LIB
$(LIBURB_BIG_TARGET): $(LIBURB_DIR)/$(LIB_BIG_TARGET)
	cp -f $< $@
endif
$(URB_EGG_TARGET): $(URB_EGG_DIR)/dist/$(URB_EGG_NAME)
	mkdir -p $(@D)
	cp -f $< $@


distclean:
	rm -rf dist

env:
	@echo "WHATOS_SRC=$(WHATOS_SRC)"
	@echo "$(WHATOS_SRC)/$(WHATOS)"
	@echo "PYVERS=$(PYVERS)"
	@echo "PYPLATFORM=$(PYPLATFORM)"
	@echo "PYOS=$(PYOS)"
	@echo "PLATFORMSTR=$(PLATFORMSTR)"
	@echo "DIST_DIR_NAME=$(DIST_DIR_NAME)"
	@echo "DEP_ARCH=$(DEP_ARCH)"
	@echo "DEP_NOARCH=$(DEP_NOARCH)"
	@echo "DEP_ARCH_BIN=$(DEP_ARCH_BIN)"
	@echo "DEP_SDIST=$(DEP_SDIST)"
	@echo "DIST_NAME_ARCH=$(DIST_NAME_ARCH)"
	@echo "DIST_NAME_ARCH_GENERIC=$(DIST_NAME_ARCH_GENERIC)"
	@echo "DIST_NAME_NOARCH=$(DIST_NAME_NOARCH)"
	@echo "DIST_NAME_ARCH_BIN=$(DIST_NAME_ARCH_BIN)"
	@echo "DIST_NAME_SDIST=$(DIST_NAME_SDIST)"
	@echo "VERSION=$(VERSION)"
	@echo "SOVERSION=$(SOVERSION)"
	@echo "BOOST_ROOT=$(BOOST_ROOT)"


