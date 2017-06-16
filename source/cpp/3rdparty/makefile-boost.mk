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

