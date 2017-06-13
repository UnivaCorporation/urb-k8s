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


BUILDDIR=build


#-------------------------------------------------------------------------
#-------------------------------------------------------------------------
ifdef SUBDIRS
#-------------------------------------------------------------------------
#-------------------------------------------------------------------------

GOALS=$(filter-out $(FILTER_GOALS),$(filter-out $(SUBDIRS),$(MAKECMDGOALS)))

.PHONY: all install deps clean distclean test

all:  recurse

install deps clean distclean test: recurse

.PHONY: recurse
recurse: $(SUBDIRS)

.PHONY: $(SUBDIRS)
$(SUBDIRS):
# Don't build anything if we goal was passed and all were filtered
ifneq ($(strip $(GOALS)),)
	$(MAKE) -C $@ $(GOALS)
else
# Check if no goal was passed... if so we build our default target
ifeq ($(strip $(MAKECMDGOALS)),)
	$(MAKE) -C $@ 
endif
endif
endif


#-------------------------------------------------------------------------
#-------------------------------------------------------------------------
ifdef SUBMAKEFILES
#-------------------------------------------------------------------------
#-------------------------------------------------------------------------
.PHONY: all install deps clean distclean test

all: recurse

deps install clean distclean test: recurse

.PHONY: recurse
recurse: $(SUBMAKEFILES) $(SUBDIRS)

.PHONY: $(SUBMAKEFILES)
$(SUBMAKEFILES):
	$(MAKE) -f $@ $(MAKECMDGOALS)
endif
