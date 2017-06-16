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

ROOT_DIR=./protobuf-to-jsoncpp-r11
SUBDIRS=$(ROOT_DIR)

FILTER_GOALS=deps test distclean

# All needs to be first
all:

test:

distclean:
	$(MAKE) -C $(ROOT_DIR) clean

include ../../../util/include.mk
