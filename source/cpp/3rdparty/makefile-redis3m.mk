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


ROOT_DIR=./redis3m
TARGET_DIR=$(ROOT_DIR)/build
SUBDIRS=$(TARGET_DIR)

# Global goals to filter out
BASE_FILTER_GOALS=deps test distclean
export CC=gcc
export CXX=g++

ifneq ($(BOOST_ROOT),)
REDIS3M_BOOST=-DBOOST_ROOT=$(BOOST_ROOT)
endif
ifneq ($(Boost_INCLUDE_DIR),)
REDIS3M_BOOST_INC=-DBoost_INCLUDE_DIR=$(Boost_INCLUDE_DIR)
endif

# If we don't have a build dir addtionally filter clean targets
ifeq ($(wildcard $(TARGET_DIR)/Makefile),)
FILTER_GOALS=$(BASE_FILTER_GOALS) distclean clean
else
FILTER_GOALS=$(BASE_FILTER_GOALS)
endif

# Determine which Cmake to use
ifneq ($(DEBUG_BUILD),)
REDIS3M_DEBUG_BUILD="-DCMAKE_BUILD_TYPE=DEBUG"
endif

all: $(TARGET_DIR)/Makefile

deps test: $(TARGET_DIR)/Makefile

$(TARGET_DIR)/Makefile: $(ROOT_DIR)/CMakeLists.txt
	mkdir -p $(TARGET_DIR)
	cd $(TARGET_DIR) && $(CMAKE) $(REDIS3M_DEBUG_BUILD) -DBoost_NO_BOOST_CMAKE=ON $(REDIS3M_BOOST) $(REDIS3M_BOOST_INC) -G "Unix Makefiles" ../

distclean:
	rm -rf $(TARGET_DIR)

include ../../../util/include.mk
