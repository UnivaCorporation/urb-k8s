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

ROOT_DIR=./libb64-1.2.1
SUBDIRS=$(ROOT_DIR)

FILTER_GOALS=deps test distclean
export CC=gcc
export MAKE

# All needs to be first
all:
	$(MAKE) -C $(ROOT_DIR)

test:

distclean:
	$(MAKE) -C $(ROOT_DIR) clean

include ../../../util/include.mk
