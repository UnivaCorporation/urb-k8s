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


BOOST_TARGZ=$(shell $(FIND) . -maxdepth 2 -name boost-[0-9]\*tar.gz -exec basename {} \;)
BOOST_VER_DIR=$(shell basename $(BOOST_TARGZ) .tar.gz)
ROOT_DIR=./boost
TARGET_DIR=$(ROOT_DIR)/$(BOOST_VER_DIR)

all: $(TARGET_DIR)/boost

deps test: $(TARGET_DIR)/boost

$(TARGET_DIR)/boost:
	cd $(ROOT_DIR); $(TAR) xzf $(BOOST_TARGZ)

distclean:
	rm -rf $(TARGET_DIR)

clean:

include ../../../util/include.mk

