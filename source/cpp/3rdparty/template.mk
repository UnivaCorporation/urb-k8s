#######################################################################
##                                                                   ##
##   Copyright (c) 2014, Univa.  All rights reserved.                ##
##   http://www.univa.com                                            ##
##                                                                   ##
##   License:                                                        ##
##     Univa                                                         ##
##                                                                   ##
##                                                                   ##
#######################################################################

# ROOT_DIR needs to be set...

#TODO: This should be able to use or variable but the targets in 
# include.mk mess up our targets if we include too early.
TARGET_DIR=$(ROOT_DIR)/build
SUBDIRS=$(TARGET_DIR)

ifneq ($(DEBUG_BUILD),)
CONFIGURE_ENV+=CFLAGS="-g3 -O0 -UNDEBUG -DDEBUG -Wno-unused-local-typedefs" CXXFLAGS="-g3 -O0 -UNDEBUG -DDEBUG -Wno-unused-local-typedefs"
else
CONFIGURE_ENV+=CFLAGS="-Wno-unused-local-typedefs" CXXFLAGS="-Wno-unused-local-typedefs"
endif

# Args to pass to all configure commands
BASE_CONFIGURE_ARGS=--enable-shared=no --with-pic

# Global goals to filter out
BASE_FILTER_GOALS=deps test

# If we don't have a build dir addtionally filter clean targets
ifeq ($(wildcard $(TARGET_DIR)/Makefile),) 
FILTER_GOALS=$(BASE_FILTER_GOALS) distclean clean
else
FILTER_GOALS=$(BASE_FILTER_GOALS)
endif


all: $(TARGET_DIR)/Makefile

deps test: $(TARGET_DIR)/Makefile

distclean:
	rm -rf $(TARGET_DIR)

$(TARGET_DIR)/Makefile: $(ROOT_DIR)/configure
	mkdir -p $(TARGET_DIR)
	cd $(TARGET_DIR) && $(CONFIGURE_ENV) ../configure $(BASE_CONFIGURE_ARGS)


include ../../../util/include.mk
