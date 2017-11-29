default: all

# Stubs for default targets
.PHONY:deps install clean dist distclean test env
deps install test:

include ../../../../util/include.mk

DIST_DIR=dist

REDIS_ARCHIVE=$(shell ls redis-*.tar.gz)
REDIS_NAME=$(subst .tar.gz,,$(REDIS_ARCHIVE))

TAR?=tar
CC=gcc
export CC
export MAKE

ifeq ($(DEBUG_BUILD),)
# disable debug flags by setting empty variable, jmalloc flags taken from underlying makefile
REDIS_DEBUG_ENV= DEBUG_FLAGS= JEMALLOC_CFLAGS="-std=gnu99 -Wall -pipe -O3 -funroll-loops $(CFLAGS)"
else
REDIS_DEBUG_ENV= JEMALLOC_CFLAGS="-std=gnu99 -Wall -pipe -g3 -O3 -funroll-loops $(CFLAGS)" CFLAGS="-g3 -O0 $(CFLAGS)"
endif

distclean: clean

all: $(BUILDDIR)/.dummy $(BUILDDIR)/$(REDIS_NAME)/src/redis-server

$(DIST_DIR)/.dummy: 
	mkdir -p $(DIST_DIR)
	touch $@

$(BUILDDIR)/.dummy: 
	mkdir -p $(BUILDDIR)
	touch $@

$(BUILDDIR)/$(REDIS_NAME)/src/redis-server: $(REDIS_ARCHIVE)
	$(TAR) xzvf $< -C $(BUILDDIR)
	$(SED) -i 's/^JEMALLOC_CFLAGS.*$$/JEMALLOC_CFLAGS+=$$(CFLAGS)/' $(BUILDDIR)/$(REDIS_NAME)/deps/Makefile
	cd $(BUILDDIR)/$(REDIS_NAME) && $(REDIS_DEBUG_ENV) $(MAKE) REDIS_LDFLAGS="-lrt"
	
dist: $(DIST_DIR)/.dummy $(BUILDDIR)/.dummy $(DIST_DIR)/bin/redis-server

$(DIST_DIR)/bin/redis-server: $(BUILDDIR)/$(REDIS_NAME)/src/redis-server
	cd $(BUILDDIR)/$(REDIS_NAME) && $(MAKE) install PREFIX=../../../$(DIST_DIR)
	cp -r -f $(BUILDDIR)/$(REDIS_NAME)/utils $(DIST_DIR)
	cp -f $(BUILDDIR)/$(REDIS_NAME)/redis.conf $(DIST_DIR)

clean:
	rm -rf $(BUILDDIR) $(DIST_DIR)

