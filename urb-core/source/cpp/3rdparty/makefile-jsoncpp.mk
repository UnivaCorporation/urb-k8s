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


ROOT_DIR=./jsoncpp-1.8.3
TARGET_DIR=$(ROOT_DIR)/build
SUBDIRS=$(TARGET_DIR)

# Global goals to filter out
BASE_FILTER_GOALS=deps test distclean
export CC=gcc
export CXX=g++

ifneq ($(DEBUG_BUILD),)
CMAKEBUILDTYPE=-DCMAKE_BUILD_TYPE=Debug
else
CMAKEBUILDTYPE=-DCMAKE_BUILD_TYPE=Release
endif

# If we don't have a build dir addtionally filter clean targets
ifeq ($(wildcard $(TARGET_DIR)/Makefile),)
FILTER_GOALS=$(BASE_FILTER_GOALS) distclean clean
else
FILTER_GOALS=$(BASE_FILTER_GOALS)
endif

# Determine which Cmake to use
#ifeq (,$(findstring cmake28,$(shell which cmake28 2> /dev/null)))
#CMAKE=cmake28
#else
#CMAKE=cmake
#endif

all: $(TARGET_DIR)/Makefile

deps test: $(TARGET_DIR)/Makefile

$(TARGET_DIR)/Makefile: $(ROOT_DIR)/CMakeLists.txt
	mkdir -p $(TARGET_DIR)
	cd $(TARGET_DIR) && $(CMAKE) $(CMAKEBUILDTYPE) -DCMAKE_CXX_FLAGS=-fPIC -DBUILD_STATIC_LIBS=ON -DBUILD_SHARED_LIBS=OFF -G "Unix Makefiles" ../ && make

distclean:
	rm -rf $(TARGET_DIR)

include ../../../util/include.mk
