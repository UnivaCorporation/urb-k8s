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

ROOT_DIR=./protobuf-2.6.1
SUBDIRS=$(ROOT_DIR)

FILTER_GOALS=deps test distclean
export MAKE

# All needs to be first
all:
	$(MAKE) -C $(ROOT_DIR) dist

test:

distclean:
	$(MAKE) -C $(ROOT_DIR) clean

include ../../../util/include.mk
