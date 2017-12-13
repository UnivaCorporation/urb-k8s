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


PICOJSON_TARGZ=$(shell $(FIND) . -maxdepth 2 -name picojson-[0-9]\*tar.gz -exec basename {} \;)
PICOJSON_VER_DIR=$(shell basename $(PICOJSON_TARGZ) .tar.gz)
PICOJSON_DIR=./picojson
TARGET_DIR=$(PICOJSON_DIR)/$(PICOJSON_VER_DIR)

all: $(TARGET_DIR)/picojson

deps test: $(TARGET_DIR)/picojson

# include file library - nothing to build
$(TARGET_DIR)/picojson:
	cd $(PICOJSON_DIR); $(TAR) xzf $(PICOJSON_TARGZ)

distclean:
	rm -rf $(TARGET_DIR)

clean:

env:
	@echo "PICOJSON_TARGZ=$(PICOJSON_TARGZ)"
	@echo "PICOJSON_VER_DIR=$(PICOJSON_VER_DIR)"
	@echo "TARGET_DIR=$(TARGET_DIR)"

include ../../../util/include.mk

