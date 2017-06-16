default: all

# Stubs for default targets
.PHONY:deps install clean dist distclean test env
deps install test:

include ../../../../util/include.mk

#DIST_DIR=dist

PROTOBUF_ARCHIVE=$(shell ls protobuf-*.tar.gz)
PROTOBUF_NAME=$(subst .tar.gz,,$(PROTOBUF_ARCHIVE))
#PROTO_LIB=$(BUILDDIR)/$(PROTOBUF_NAME)/src/.libs/libprotoc.a

ifeq ($(shell uname -s),SunOS)
  ifeq ($(shell uname -p),i386) 
    CONFIGURE_ENV=CXXFLAGS=-m32
  endif
endif

TAR?=tar
CC=gcc
export CC
export MAKE

distclean: clean

all: $(BUILDDIR)/.dummy protobuf
#all: $(BUILDDIR)/.dummy $(PROTO_LIB)

#$(DIST_DIR)/.dummy: 
#	mkdir -p $(DIST_DIR)
#	touch $@

$(BUILDDIR)/.dummy: 
	mkdir -p $(BUILDDIR)
	touch $@

protobuf: $(PROTOBUF_ARCHIVE)
#$(PROTO_LIB): $(PROTOBUF_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	cd $(BUILDDIR)/$(PROTOBUF_NAME)/gtest && $(CONFIGURE_ENV) ./configure --enable-shared=no --with-pic && $(MAKE)
	cd $(BUILDDIR)/$(PROTOBUF_NAME) && $(CONFIGURE_ENV) ./configure --enable-shared=no --with-pic && $(MAKE)


#dist: $(DIST_DIR)/.dummy $(BUILDDIR)/.dummy protobuf

clean:
	rm -rf $(BUILDDIR) $(DIST_DIR)

