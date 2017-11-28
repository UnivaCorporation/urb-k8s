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

include ../../../util/include.mk

GOOGLETEST_TARGZ=$(shell $(FIND) . -maxdepth 2 -name googletest*-[0-9]\*tar.gz -exec basename {} \;)
GOOGLETEST_VER_DIR=$(shell basename $(GOOGLETEST_TARGZ) .tar.gz)
ROOT_DIR=./googletest/$(GOOGLETEST_VER_DIR)
TARGET_DIR=$(ROOT_DIR)/build
SUBDIRS=$(TARGET_DIR)

# Global goals to filter out
BASE_FILTER_GOALS=deps test distclean
export CC=gcc
export CXX=g++

# If we don't have a build dir addtionally filter clean targets
ifeq ($(wildcard $(TARGET_DIR)/Makefile),)
FILTER_GOALS=$(BASE_FILTER_GOALS) distclean clean
else
FILTER_GOALS=$(BASE_FILTER_GOALS)
endif

all: $(TARGET_DIR)/Makefile

deps test: $(TARGET_DIR)/Makefile

#$(TARGET_DIR)/Makefile: $(ROOT_DIR)/CMakeLists.txt
$(TARGET_DIR)/Makefile:
	cd googletest && $(TAR) xzf $(GOOGLETEST_TARGZ)
	mkdir -p $(TARGET_DIR)
	cd $(TARGET_DIR) && $(CMAKE) -DBUILD_GTEST=ON -DBUILD_GMOCK=OFF -G "Unix Makefiles" ../ && make

clean:
	cd $(TARGET_DIR) && make clean

distclean:
	rm -rf $(TARGET_DIR)

env:
	@echo "GOOGLETEST_TARGZ=$(GOOGLETEST_TARGZ)"
	@echo "GOOGLETEST_VER_DIR=$(GOOGLETEST_VER_DIR)"
	@echo "ROOT_DIR=$(ROOT_DIR)"
	@echo "TARGET_DIR=$(TARGET_DIR)"


#include ../../../util/include.mk
