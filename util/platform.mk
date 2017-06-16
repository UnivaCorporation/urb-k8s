########################################################################
##                                                                   ##
##   Copyright (c) 2014, Univa.  All rights reserved.                ##
##   http://www.univa.com                                            ##
##                                                                   ##
##   License:                                                        ##
##     Univa                                                         ##
##                                                                   ##
##                                                                   ##
#######################################################################

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
