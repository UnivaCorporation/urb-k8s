# Copyright 2017 Univa Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# The Liburb shared library and archive file
DEFAULT_LIB_PATH=/usr/local/lib

# Java Environment
JAVA_HOME?=/usr/java/jdk1.7.0_67-cloudera
JDK_DIR=$(JAVA_HOME)
JDK_INC=-I$(JDK_DIR)/include -I$(JDK_DIR)/include/linux


# Local Environment
DIR=$(CPP_BASE)/$(NAME)
SRC_DIR=$(DIR)/source
TEST_DIR=$(DIR)/test
INC_DIR=$(BUILD_DIR)/include
BUILD_DIR=$(DIR)/$(BUILDDIR)
LOCAL_INC=-I$(INC_DIR) -I$(INC_DIR)/common

# Python bindings include file
BINDINGS_INCLUDE=$(BUILD_DIR)/python_bindings.mk
BINDINGS_INCLUDE_DIR=$(BUILD_DIR)/bindings_include


DISABLED_WARNINGS=-Wno-unused-local-typedefs -Wno-unused-parameter
ENABLED_WARNINGS=-Wredundant-decls -Wswitch-default # -Wshadow -Wundef -Wfloat-equal -Wconversion
PICOJSON_FLAGS=-DPICOJSON_USE_INT64 -D__STDC_FORMAT_MACROS

CFLAGS=-Wall -fPIC -Wextra $(DISABLED_WARNINGS) $(ENABLED_WARNINGS) $(PICOJSON_FLAGS) $(JSONCPP_FLAGS)
LDFLAGS=-shared -Wl,-soname,$(LIB_SONAME)
ifdef DEBUG_BUILD
  CFLAGS += -DDEBUG -O0 -g3
else
  CFLAGS += -DNDEBUG -O2
endif

ifeq ($(shell uname -s),SunOS)
  CFLAGS += -pthreads
else
  CFLAGS += -pthread
  LD_WARN_COMMON=-Wl,-warn-common
  LDFLAGS += $(LD_WARN_COMMON)
endif

ifeq ($(STDCPP11),true)
  CFLAGS += -std=c++11 -std=c++1y
else
  CFLAGS += -std=c++0x -DGTEST_HAS_TR1_TUPLE=0 # required to build tests with gtest
endif

#Python stuff
VIRTUALENV=$(BUILD_DIR)/testpy
PYTHONSRC=$(DIR)/python-bindings
PYTHONEGG=$(PYTHONSRC)/dist/mesos-$(EXT_MESOS_VERSION)-py$(EGG_PYV)-$(EGG_ARCH).egg

# CPP Variables
CPP_BASE=$(TOP)/source/cpp

# on some systems (CentOS 6.5) installed in separate directory (usually ev.h is in /usr/include)
LIBEV_INC=-I/usr/include/libev

## Google Log (glog)
GLOG_BASE=$(CPP_BASE)/3rdparty/glog-0.3.3
GLOG_INC=-I$(GLOG_BASE)/src -I$(GLOG_BASE)/$(BUILDDIR)/src
GLOG_LIB=-L$(GLOG_BASE)/$(BUILDDIR)/.libs -lglog

## Google Protobuf (protobuf)
PROTO_NAME=protobuf-3.3.0
PROTO_BASE=$(CPP_BASE)/3rdparty/$(PROTO_NAME)/build/$(PROTO_NAME)
PROTO_INC=-I$(PROTO_BASE)/src
PROTO_LIB=-L$(PROTO_BASE)/src/.libs -lprotobuf
PROTO_ARCHIVE=$(PROTO_BASE)/src/.libs/libprotobuf.a

## Google Test (gtest)
GTEST_BASE=$(CPP_BASE)/3rdparty/googletest/googletest-release-1.8.0
GTEST_INC=-I$(GTEST_BASE)/googletest/include
GTEST_LIB=-L$(GTEST_BASE)/build/googletest -lgtest -lgtest_main

## redism3
REDIS3M_BASE=$(CPP_BASE)/3rdparty/redis3m
REDIS3M_INC=-I$(REDIS3M_BASE)/include
REDIS3M_LIB=-L$(REDIS3M_BASE)/build -lredis3m

## jsoncpp
JSONCPP_BASE=$(CPP_BASE)/3rdparty/jsoncpp-1.8.3
JSONCPP_INC=-I$(JSONCPP_BASE)/include
JSONCPP_LIB=$(JSONCPP_BASE)/build/src/lib_json/libjsoncpp.a

## picojson
PICOJSON_BASE=$(CPP_BASE)/3rdparty/picojson
PICOJSON_INC=-I$(PICOJSON_BASE)/picojson-1.3.0

## Base64 library
B64_BASE=$(CPP_BASE)/3rdparty/libb64-1.2.1
B64_INC=-I$(B64_BASE)/include
B64_LIB=$(B64_BASE)/src/libb64.a

## protobuf-to-jsoncpp-r11
PBTJ_BASE=$(CPP_BASE)/3rdparty/protobuf-to-jsoncpp-r11
PBTJ_INC=-I$(PBTJ_BASE)
PBTJ_LIB=$(PBTJ_BASE)/libjson_protobuf.a

## redis
REDIS_VER=4.0.2
REDIS_BASE=$(CPP_BASE)/3rdparty/redis
REDIS_BIN=$(REDIS_BASE)/build/redis-$(REDIS_VER)/src

## hiredis - use redis dependency
#TODO: If we fix the callback we won't need this include
HIREDIS_BASE=$(REDIS_BASE)/build/redis-$(REDIS_VER)/deps/hiredis
HIREDIS_INC=-I$(HIREDIS_BASE)
HIREDIS_LIB=$(HIREDIS_BASE)/libhiredis.a

## stout
STOUT_BASE=$(CPP_BASE)/3rdparty
STOUT_INC=-I$(STOUT_BASE)


ifdef BOOST_ROOT
BOOST_INC=-I$(BOOST_ROOT)
endif

EXT_INC=$(GLOG_INC) $(PROTO_INC) $(REDIS3M_INC) $(PBTJ_INC) $(JSONCPP_INC) $(HIREDIS_INC) $(LIBEV_INC) $(PICOJSON_INC) $(STOUT_INC)
INCS=$(LOCAL_INC) $(EXT_INC) $(BOOST_INC) $(JDK_INC)
TEST_INCS=$(INCS) $(GTEST_INC) -I$(MESOS_DIR)

## Linker Options
EXT_OBJ=
EXT_LIB=$(JSONCPP_LIB) $(GLOG_LIB) $(PROTO_LIB) $(REDIS3M_LIB) $(HIREDIS_LIB) $(PBTJ_LIB) $(B64_LIB)

EXT_MESOS_OBJ= \
$(EXT_MESOS_SRC_DIR)/build/src/java/jni/.libs/libjava_la-org_apache_mesos_Log.o \
$(EXT_MESOS_SRC_DIR)/build/src/java/jni/.libs/libjava_la-org_apache_mesos_state_ZooKeeperState.o \
$(EXT_MESOS_SRC_DIR)/build/src/java/jni/.libs/libjava_la-org_apache_mesos_state_AbstractState.o \
$(EXT_MESOS_SRC_DIR)/build/src/java/jni/.libs/libjava_la-org_apache_mesos_state_LevelDBState.o \
$(EXT_MESOS_SRC_DIR)/build/src/java/jni/.libs/libjava_la-org_apache_mesos_state_Variable.o \
$(EXT_MESOS_SRC_DIR)/build/src/zookeeper/.libs/libmesos_no_3rdparty_la-zookeeper.o \
$(EXT_MESOS_SRC_DIR)/build/src/zookeeper/.libs/libmesos_no_3rdparty_la-group.o \
$(EXT_MESOS_SRC_DIR)/build/src/zookeeper/.libs/libmesos_no_3rdparty_la-authentication.o \
$(EXT_MESOS_SRC_DIR)/build/src/zookeeper/.libs/libmesos_no_3rdparty_la-detector.o \
$(EXT_MESOS_SRC_DIR)/build/src/zookeeper/.libs/libmesos_no_3rdparty_la-contender.o \
$(EXT_MESOS_SRC_DIR)/build/include/mesos/state/.libs/libmesos_no_3rdparty_la-state.pb.o

EXT_MESOS_LIB= \
$(EXT_MESOS_SRC_DIR)/build/src/.libs/libstate.a \
-Wl,-whole-archive \
$(EXT_MESOS_SRC_DIR)/build/3rdparty/zookeeper-*/src/c/.libs/libzookeeper_mt.a  \
$(EXT_MESOS_SRC_DIR)/build/3rdparty/libprocess/.libs/libprocess.a \
$(EXT_MESOS_SRC_DIR)/build/src/.libs/liblog.a \
-Wl,-no-whole-archive  \
$(EXT_MESOS_SRC_DIR)/build/3rdparty/leveldb-1.4/libleveldb.a

LIBS=$(EXT_LIB) -lev -lz -luuid
ifeq ($(shell uname -s),SunOS)
TEST_LIBS=$(GTEST_LIB) -lpthread -lev -lsocket -lnsl -lresolv
else
TEST_LIBS=$(GTEST_LIB) -lpthread -lev
endif


# Stock Mesos stuff
## Protobuf stuff
#MESOS_DIR=$(DIR)/mesos
MESOS_DIR=$(INC_DIR)/mesos
PROTOC=$(CPP_BASE)/3rdparty/$(PROTO_NAME)/$(BUILDDIR)/$(PROTO_NAME)/src/protoc

MESOS_PROTO_DIR=$(MESOS_DIR)
PROTO_FILE=$(MESOS_PROTO_DIR)/mesos.proto
MESOS_PROTO_BASE=mesos.pb
MESOS_PBO=$(MESOS_PROTO_BASE).o
MESOS_PBH=$(MESOS_PROTO_BASE).h
MESOS_PBC=$(MESOS_PROTO_BASE).cc

MESOS_RESOURCE_PROVIDER_DIR=$(MESOS_DIR)
RESOURCE_PROVIDER_PROTO_FILE=$(MESOS_RESOURCE_PROVIDER_DIR)/resource_provider.proto
MESOS_RESOURCE_PROVIDER_PROTO_BASE=resource_provider.pb
MESOS_RESOURCE_PROVIDER_PBO=$(MESOS_RESOURCE_PROVIDER_PROTO_BASE).o
MESOS_RESOURCE_PROVIDER_PBH=$(MESOS_RESOURCE_PROVIDER_PROTO_BASE).h
MESOS_RESOURCE_PROVIDER_PBC=$(MESOS_RESOURCE_PROVIDER_PROTO_BASE).cc

MESOS_MESSAGES_DIR=$(MESOS_DIR)
MESSAGES_PROTO_FILE=$(MESOS_MESSAGES_DIR)/messages.proto
MESOS_MESSAGES_PROTO_BASE=messages.pb
MESOS_MESSAGES_PBO=$(MESOS_MESSAGES_PROTO_BASE).o
MESOS_MESSAGES_PBH=$(MESOS_MESSAGES_PROTO_BASE).h
MESOS_MESSAGES_PBC=$(MESOS_MESSAGES_PROTO_BASE).cc

MESOS_SCHEDULER_DIR=$(MESOS_DIR)
SCHEDULER_PROTO_FILE=$(MESOS_SCHEDULER_DIR)/scheduler.proto
MESOS_SCHEDULER_PROTO_BASE=scheduler.pb
MESOS_SCHEDULER_PBO=$(MESOS_SCHEDULER_PROTO_BASE).o
MESOS_SCHEDULER_PBH=$(MESOS_SCHEDULER_PROTO_BASE).h
MESOS_SCHEDULER_PBC=$(MESOS_SCHEDULER_PROTO_BASE).cc

MESOS_AUTHENTICATION_DIR=$(MESOS_DIR)
AUTHENTICATION_PROTO_FILE=$(MESOS_AUTHENTICATION_DIR)/authentication.proto
MESOS_AUTHENTICATION_PROTO_BASE=authentication.pb
MESOS_AUTHENTICATION_PBO=$(MESOS_AUTHENTICATION_PROTO_BASE).o
MESOS_AUTHENTICATION_PBH=$(MESOS_AUTHENTICATION_PROTO_BASE).h
MESOS_AUTHENTICATION_PBC=$(MESOS_AUTHENTICATION_PROTO_BASE).cc


MESOS_FETCHER_DIR=$(MESOS_DIR)/fetcher
FETCHER_PROTO_FILE=$(MESOS_FETCHER_DIR)/fetcher.proto
MESOS_FETCHER_PROTO_BASE=fetcher.pb
MESOS_FETCHER_PBO=$(MESOS_FETCHER_PROTO_BASE).o
MESOS_FETCHER_PBH=$(MESOS_FETCHER_PROTO_BASE).h
MESOS_FETCHER_PBC=$(MESOS_FETCHER_PROTO_BASE).cc

MESOS_OBJS= \
$(BUILDDIR)/$(MESOS_PBO) $(BUILDDIR)/$(MESOS_RESOURCE_PROVIDER_PBO) $(BUILDDIR)/$(MESOS_MESSAGES_PBO) $(BUILDDIR)/$(MESOS_SCHEDULER_PBO) \
$(BUILDDIR)/$(MESOS_AUTHENTICATION_PBO) $(BUILDDIR)/$(MESOS_FETCHER_PBO)

FETCHER_EXTRA_CPP=$(INC_DIR)/logging/logging.cpp $(INC_DIR)/logging/flags.cpp $(INC_DIR)/slave/containerizer/fetcher.cpp
FETCHER_EXTRA_INC=-I$(CPP_BASE)/3rdparty/libprocess/include -I$(INC_DIR)/slave/containerizer

FETCHER_CPP=$(DIR)/mesos/fetcher.cpp
FETCHER=$(BUILD_DIR)/fetcher
FETCHER_LIBS=$(LIB_NAME) -lpthread -lcurl

# CPP Compilation Rules
## Normal Sources and objects
SRCS=$(subst $(SRC_DIR)/,,$(shell find $(SRC_DIR) -name '*.cpp'))
BASEOBJS=$(addprefix $(BUILDDIR)/,$(subst .cpp,.o, $(SRCS)))
HEADERS=$(shell find $(SRC_DIR) -name '*.h*')
BASE_INCS=$(addprefix $(INC_DIR)/,$(subst $(SRC_DIR)/,,$(HEADERS)))


## Test Sources and programs
# randomize test order
TEST_SRCS=$(shell for f in `find $(TEST_DIR) -name '*.cpp' -print`; do echo "$$RANDOM $$f"; done | sort -n | cut -d' ' -f2)
#TEST_SRCS=$(shell find $(TEST_DIR) -name '*.cpp')
TESTS=$(subst $(TEST_DIR)/,,$(TEST_SRCS))
TEST_PROGS=$(addprefix $(BUILD_DIR)/,$(subst .cpp,.test, $(TESTS)))
TEST_OUTPUTS=$(filter $(BUILD_DIR)/test_%,$(addsuffix .xml,$(TEST_PROGS)))
VALGRIND_OUTPUTS=$(filter $(BUILD_DIR)/test_%,$(addsuffix .valgrind,$(TEST_PROGS)))
#TEST_OUTPUTS=$(addsuffix .xml,$(TEST_PROGS))

# Add in the objects that are 'generated'
OBJS=$(BUILDDIR)/build_version.o $(MESOS_OBJS) $(BASEOBJS)

.PHONY:all clean test env distclean deps install default rmtest valgrind

default:

SUBDIRS = python-bindings

include ../../../util/include.mk

# Build everthing
default: $(BUILDDIR) $(BASE_INCS) $(FETCHER) $(TEST_PROGS) $(LIB_TARGET) $(ARCHIVE_NAME) $(BINDINGS_INCLUDE) all

ifdef FULL_MESOS_LIB
all: $(LIB_BIG_TARGET)
endif


# Helper goal to print environment
env:
	@echo SRCS: $(SRCS)
	@echo HEADERS: $(HEADERS)
	@echo TEST_SRCS: $(TEST_SRCS)
	@echo TESTS: $(TESTS)
	@echo OBJS: $(OBJS)
	@echo BASE_INCS: $(BASE_INCS)
	@echo TEST_PROGS: $(TEST_PROGS)
	@echo BUILDDIR: $(BUILDDIR)
	@echo TEST_OUTPUTS: $(TEST_OUTPUTS)
	@echo DIR: $(DIR)
	@echo MESOS_DIR: $(MESOS_DIR)
	@echo INC_DIR: $(INC_DIR)
	@echo CPP_BASE: $(CPP_BASE)
	@echo FETCHER: $(FETCHER)
	@echo CFLAGS: $(CFLAGS)
	@echo CXXFLAGS: $(CXXFLAGS)
	@echo GCCVERSION: $(GCCVERSION)
	@echo EXT_MESOS_VERSION: $(EXT_MESOS_VERSION)

# Nothing to do
install:

# Nothing to do
deps:

# Compile the stock mesos .proto file
#$(INC_DIR)/$(MESOS_PBH) $(INC_DIR)/$(MESOS_PBC): $(PROTO_FILE)
$(MESOS_PROTO_DIR)/$(MESOS_PBH) $(MESOS_PROTO_DIR)/$(MESOS_PBC): $(PROTO_FILE)
	cd $(MESOS_PROTO_DIR) && $(PROTOC) --proto_path $(MESOS_PROTO_DIR) $< --cpp_out . --python_out .

#$(INC_DIR)/$(MESOS_MESSAGES_PBH) $(INC_DIR)/$(MESOS_MESSAGES_PBC): $(MESSAGES_PROTO_FILE)
$(MESOS_MESSAGES_DIR)/$(MESOS_MESSAGES_PBH) $(MESOS_MESSAGES_DIR)/$(MESOS_MESSAGES_PBC): $(MESSAGES_PROTO_FILE)
	cd $(MESOS_MESSAGES_DIR) && $(PROTOC) --proto_path $(MESOS_MESSAGES_DIR) $< --cpp_out .

#$(INC_DIR)/$(MESOS_SCHEDULER_PBH) $(INC_DIR)/$(MESOS_SCHEDULER_PBC): $(SCHEDULER_PROTO_FILE)
$(MESOS_SCHEDULER_DIR)/$(MESOS_SCHEDULER_PBH) $(MESOS_SCHEDULER_DIR)/$(MESOS_SCHEDULER_PBC): $(SCHEDULER_PROTO_FILE)
	cd $(MESOS_SCHEDULER_DIR) && $(PROTOC) --proto_path $(MESOS_SCHEDULER_DIR)/../.. --proto_path $(MESOS_SCHEDULER_DIR) $< --cpp_out .

$(MESOS_AUTHENTICATION_DIR)/$(MESOS_AUTHENTICATION_PBH) $(MESOS_AUTHENTICATION_DIR)/$(MESOS_AUTHENTICATION_PBC): $(AUTHENTICATION_PROTO_FILE)
	cd $(MESOS_AUTHENTICATION_DIR) && $(PROTOC) --proto_path $(MESOS_AUTHENTICATION_DIR)/../.. --proto_path $(MESOS_AUTHENTICATION_DIR) $< --cpp_out .

#$(INC_DIR)/$(MESOS_FETCHER_PBH) $(INC_DIR)/$(MESOS_FETCHER_PBC): $(FETCHER_PROTO_FILE)
$(MESOS_FETCHER_DIR)/$(MESOS_FETCHER_PBH) $(MESOS_FETCHER_DIR)/$(MESOS_FETCHER_PBC): $(FETCHER_PROTO_FILE)
	cd $(MESOS_FETCHER_DIR) && $(PROTOC) --proto_path $(MESOS_FETCHER_DIR) --proto_path $(MESOS_FETCHER_DIR)/.. $< --cpp_out .

$(MESOS_RESOURCE_PROVIDER_DIR)/$(MESOS_RESOURCE_PROVIDER_PBH) $(MESOS_RESOURCE_PROVIDER_DIR)/$(MESOS_RESOURCE_PROVIDER_PBC): $(RESOURCE_PROVIDER_PROTO_FILE)
	cd $(MESOS_RESOURCE_PROVIDER_DIR) && $(PROTOC) --proto_path $(MESOS_RESOURCE_PROVIDER_DIR) $< --cpp_out .


# Compile the stock mesos .proto file (separate from normal sources
# since it is a generated cpp file).
$(BUILDDIR)/$(MESOS_PBO): $(MESOS_PROTO_DIR)/mesos.pb.cc
	echo $(BUILDDIR)/$(MESOS_PBO)
	g++ $(CFLAGS) -c $(INCS) $< -o $@

$(BUILDDIR)/$(MESOS_MESSAGES_PBO): $(MESOS_MESSAGES_DIR)/messages.pb.cc
	echo $(BUILDDIR)/$(MESOS_MESSAGES_PBO)
	g++ $(CFLAGS) -c $(INCS) -I$(MESOS_PROTO_DIR) $< -o $@

$(BUILDDIR)/$(MESOS_SCHEDULER_PBO): $(MESOS_SCHEDULER_DIR)/scheduler.pb.cc
	g++ $(CFLAGS) -c $(INCS) -I$(MESOS_SCHEDULER_DIR) $< -o $@

$(BUILDDIR)/$(MESOS_AUTHENTICATION_PBO): $(MESOS_AUTHENTICATION_DIR)/authentication.pb.cc
	g++ $(CFLAGS) -c $(INCS) -I$(MESOS_AUTHENTICATION_DIR) $< -o $@

$(BUILDDIR)/$(MESOS_RESOURCE_PROVIDER_PBO): $(MESOS_RESOURCE_PROVIDER_DIR)/resource_provider.pb.cc
	g++ $(CFLAGS) -c $(INCS) -I$(MESOS_RESOURCE_PROVIDER_DIR)/.. $< -o $@

$(BUILDDIR)/$(MESOS_FETCHER_PBO): $(MESOS_FETCHER_DIR)/fetcher.pb.cc
	g++ $(CFLAGS) -c $(INCS) -I$(MESOS_FETCHER_DIR)/.. $< -o $@



$(FETCHER): $(FETCHER_CPP) $(LIB_TARGET)
	cd $(BUILD_DIR) && g++ $(CFLAGS) $(INCS) -I$(MESOS_DIR) -I$(MESOS_DIR)/fetcher $(FETCHER_EXTRA_INC) -Wl,-rpath,`pwd` $< $(FETCHER_EXTRA_CPP) $(FETCHER_LIBS) $(GLOG_LIB) -o $@

$(BUILDDIR)/build_version.o: $(BUILDDIR)/build_version.cpp
	g++ $(CFLAGS) -c $< -o $@

$(BUILDDIR)/build_version.cpp: 
	@echo "const char *build1=\"GIT: Commit: $(shell git log -1 --pretty=%H)\";" > "$@"
	@echo "const char *build2=\"GIT: Date: $(shell git log -1 --pretty=%cd)\";" >> "$@"
	@echo "const char *build3=\"GIT: Branch: $(shell git symbolic-ref HEAD)\";" >> "$@"
	@echo "const char *build4=\"GIT: Tag: $(shell git describe)\";" >> "$@"
	@echo "const char *build5=\"GIT: Jenkins Build Tag: $(BUILD_TAG)\";" >> "$@"
	@echo "const char *build6=\"GIT: URB Version: $(VERSION)\";" >> "$@"
	@echo "const char *build7=\"GIT: Mesos Version: $(EXT_MESOS_VERSION)\";" >> "$@"
	@echo "const char *build8=\"GIT: Built on: $(shell uname -a)\";" >> "$@"
	@echo "const char *build9=\"GIT: Release string: $(URB_REL_STR)\";" >> "$@"


# Make the root build directory, copy mesos include file dependencies and apply stout patch
$(BUILDDIR):
	mkdir -p $@
	mkdir -p $(INC_DIR)
	cp -r mesos/include/* $(INC_DIR)
#	cd build; $(PATCH) -p5 < ../stout.patch

# Copy our header files...
$(BASE_INCS): $(HEADERS)
	cp $^ $(INC_DIR)

# Link our test programs
$(BUILD_DIR)/%.test: $(TEST_DIR)/%.cpp $(LIB_TARGET)
	cd $(BUILD_DIR) && g++ $(CFLAGS) $(TEST_INCS) $(LD_WARN_COMMON) -Wl,-rpath,`pwd` $< $(LIB_NAME) $(TEST_LIBS) -o $@

# Compile our standard sources
$(BUILDDIR)/%.o: $(BASE_INCS) $(SRC_DIR)/%.cpp $(INC_DIR)/$(MESOS_PBH) $(INC_DIR)/$(MESOS_MESSAGES_PBH)
	g++ $(CFLAGS) -c $(INCS) $< -o $@

$(BUILDDIR)/%.o: $(SRC_DIR)/%.cpp
	g++ $(CFLAGS) -c $(INCS) -I$(MESOS_DIR) $< -o $@

# Build our shared library library
$(LIB_TARGET): $(OBJS)

	g++ $(LDFLAGS) $^ $(EXT_OBJ) $(LIBS) -o $@
	cd $(BUILDDIR) && ln -sf $(LIB_NAME) $(LIB_SONAME) && ln -sf $(LIB_NAME) $(LIB_NAME_SHORT)

# Build our shared library with extra mesos junk
$(LIB_BIG_TARGET): $(OBJS)
	g++ $(LDFLAGS) $^ $(EXT_MESOS_OBJ) $(LIBS) $(EXT_MESOS_LIB) -o $@
	cd $(BUILDDIR) && ln -sf $(LIB_BIG) $(LIB_SOBIG) && ln -sf $(LIB_BIG) $(LIB_BIG_SHORT)

# Archive our built .o files
$(ARCHIVE_NAME): $(OBJS)
	$(AR) cr $@ $^

# Write out a helper makefile for bindings
$(BINDINGS_INCLUDE): $(BINDINGS_INCLUDE_DIR)
	# Export some variables for use by our bindings Makefile
	echo 'URB_PYTHON_OBJECTS=$(shell pwd)/$(LIB_TARGET)' > $@
	echo 'export URB_PYTHON_OBJECTS' >> $@
	echo 'URB_PYTHON_INCLUDE=-I$(BINDINGS_INCLUDE_DIR)' >> $@
	echo 'export URB_PYTHON_INCLUDE' >> $@

# Build the bindings include directory.  These are all of the includes required
$(BINDINGS_INCLUDE_DIR): $(MESOS_SCHEDULER_DIR)/$(MESOS_SCHEDULER_PBH) $(MESOS_PROTO_DIR)/$(MESOS_PBH) 
	mkdir $@
	mkdir $@/mesos
	mkdir $@/mesos/scheduler
	mkdir $@/google
	mkdir $@/google/protobuf
	mkdir $@/google/protobuf/io
	mkdir $@/google/protobuf/stubs
	cp -f mesos/include/mesos/executor.hpp $@/mesos
	cp -f mesos/include/mesos/mesos.hpp $@/mesos
	cp -f mesos/include/mesos/version.hpp $@/mesos
	cp -f mesos/include/mesos/scheduler.hpp $@/mesos
	cp -f mesos/include/mesos/scheduler/scheduler.hpp $@/mesos/scheduler
	cp -f $(MESOS_PROTO_DIR)/$(MESOS_PBH) $@
	cp -f $(PROTO_BASE)/src/google/protobuf/stubs/* $@/google/protobuf/stubs
	cp -f $(PROTO_BASE)/src/google/protobuf/*.h $@/google/protobuf
	cp -f $(PROTO_BASE)/src/google/protobuf/io/zero_copy_stream.h $@/google/protobuf/io
	cp -f $(PROTO_BASE)/src/google/protobuf/io/zero_copy_stream_impl.h $@/google/protobuf/io
	cp -f $(PROTO_BASE)/src/google/protobuf/io/zero_copy_stream_impl_lite.h $@/google/protobuf/io
	cp -f $(PROTO_BASE)/src/google/protobuf/io/coded_stream.h $@/google/protobuf/io
	cp -f $(MESOS_SCHEDULER_DIR)/$(MESOS_SCHEDULER_PBH) $@

# Standard clean rules
distclean clean:
	rm -rf $(BUILDDIR)

# make sure that redis is running
#redis_service:
#	if [ "$$(redis-cli ping)" != "PONG" ]; then if which systemctl >/dev/null 2>&1; then sudo systemctl redis_6379 start; else sudo service redis_6379 start; fi; fi

start_redis:
	if [ "$$($(REDIS_BIN)/redis-cli ping)" != "PONG" ]; then $(REDIS_BIN)/redis-server --protected-mode no & sleep 3; fi

stop_redis:
	if [ "$$($(REDIS_BIN)/redis-cli ping)" = "PONG" ]; then $(REDIS_BIN)/redis-cli shutdown fi

# Run our test programs.  Always remove the outputs so we allways will rerun
test: $(BUILDDIR) $(FETCHER) $(LIB_TARGET) start_redis rmtest $(TEST_OUTPUTS)
#	-qdel executor_runner.py
	-jobid=$(qstat -f -q *@$$(hostname) | grep '^[ \t]\+[0-9]\+[ \t]' | awk '/executor_runner.py/ {print $$1}') ; if [ ! -z "$$jobid" ]; then for j in $$jobid; do qdel $$j; done; fi
	$(REDIS_BIN)/redis-cli flushdb; $(REDIS_BIN)/redis-cli shutdown

# Remove test results so we can always rerun tests
rmtest: start_redis
	rm -f $(TEST_OUTPUTS)
#	-qdel executor_runner.py
	-jobid=$(qstat -f -q *@$$(hostname) | grep '^[ \t]\+[0-9]\+[ \t]' | awk '/executor_runner.py/ {print $$1}') ; if [ ! -z "$$jobid" ]; then for j in $$jobid; do qdel $$j; done; fi
	$(REDIS_BIN)/redis-cli flushdb

# Run all of the test programs trying to build XML test output
$(BUILD_DIR)/%.test.xml: $(BUILDDIR)/%.test
	PYTHON=$(PYTHON) LD_LIBRARY_PATH=$(BUILDDIR) $< --gtest_output=xml:$@

# Run tests with valgrind
$(BUILD_DIR)/%.test.valgrind: $(BUILDDIR)/%.test
	PYTHON=$(PYTHON) LD_LIBRARY_PATH=$(BUILDDIR) valgrind --read-var-info=yes --track-origins=yes --xml=yes --xml-file=$@ $<
#	PYTHON=$(PYTHON) LD_LIBRARY_PATH=$(BUILDDIR) valgrind --leak-check=full --log-file=$@ $<

valgrind: start_redis $(VALGRIND_OUTPUTS)
	-jobid=$(qstat -f -q *@$$(hostname) | grep '^[ \t]\+[0-9]\+[ \t]' | awk '/executor_runner.py/ {print $$1}') ; if [ ! -z "$$jobid" ]; then for j in $$jobid; do qdel $$j; done; fi
	$(REDIS_BIN)/redis-cli flushdb; $(REDIS_BIN)/redis-cli shutdown

# Python bindings rules
#python-bindings: $(BUILDDIR) $(PYTHONEGG)
#
#$(VIRTUALENV)/.built:
#	virtualenv $(VIRTUALENV)
#	touch $@
#
#$(VIRTUALENV)/.egg-installed: $(VIRTUALENV)/.built $(PYTHONEGG)
#	. $(VIRTUALENV)/bin/activate && easy_install $(PYTHONEGG)
#	touch $@
#
#$(PYTHONEGG): $(ARCHIVE_NAME)
#	cd $(PYTHONSRC) && URB_PYTHON_OBJECTS="$(shell pwd)/$(LIB_TARGET)" URB_PYTHON_INCLUDE="$(INCS)" python setup.py bdist_egg
#	#cd $(PYTHONSRC) && URB_PYTHON_OBJECTS="$(shell pwd)/$(ARCHIVE_NAME) $(PROTO_ARCHIVE)" URB_PYTHON_INCLUDE="$(INCS)" python setup.py bdist_egg
#
#python-bindings-test: $(BUILDDIR) $(VIRTUALENV)/.egg-installed
#	. $(VIRTUALENV)/bin/activate && ./test/test_framework.py urb://localhost
