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

ROOT_DIR=./jsoncpp-20141023
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
	cd $(TARGET_DIR) && $(CMAKE) -DJSONCPP_LIB_BUILD_SHARED=OFF -G "Unix Makefiles" ../

distclean:
	rm -rf $(TARGET_DIR)

include ../../../util/include.mk
