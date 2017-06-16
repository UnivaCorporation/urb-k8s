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

ROOT_DIR=./hiredis-20141015
SUBDIRS=$(ROOT_DIR)

FILTER_GOALS=deps test distclean
export CC=gcc
export MAKE

ifneq ($(DEBUG_BUILD),)
export OPTIMIZATION=-O0
endif

# All needs to be first
all:
	$(MAKE) -C $(ROOT_DIR) libhiredis.a

test:

distclean:
	$(MAKE) -C $(ROOT_DIR) clean

include ../../../util/include.mk
