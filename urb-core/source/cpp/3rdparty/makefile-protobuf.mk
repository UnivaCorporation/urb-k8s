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


ROOT_DIR=./protobuf-3.3.0
SUBDIRS=$(ROOT_DIR)

ifneq ($(DEBUG_BUILD),)
export CONFIGURE_ENV+=CXXFLAGS="-g3 -O0 -UNDEBUG -DDEBUG -Wno-unused-local-typedefs"
else
export CONFIGURE_ENV+=CXXFLAGS="-O2 -Wno-unused-local-typedefs"
endif

FILTER_GOALS=deps test distclean
export MAKE
# All needs to be first
all:
	mkdir -p $(ROOT_DIR)/build
	$(MAKE) -C $(ROOT_DIR) dist

test:

clean:
	$(MAKE) -C $(ROOT_DIR) clean

distclean:
	rm -rf $(ROOT_DIR)/build

#include ../../../util/include.mk
