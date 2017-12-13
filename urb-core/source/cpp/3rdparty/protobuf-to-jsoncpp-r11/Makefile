# Copyright (c) 2013, EMC Corporation (Isilon Division)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# -- Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# -- Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

CXX=		g++
PROTOC=		LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/local/lib protoc
CXXFLAGS=	-I/usr/local/include
LDFLAGS=	-L/usr/local/lib -lprotobuf -ljson
#
# CPP Variables
CPP_BASE=$(TOP)/source/cpp

## Google Protobuf (protobuf)
PROTO_NAME=$(shell basename `$(FIND) .. -maxdepth 1 -name protobuf-[0-9]\* -print`)
PROTO_BASE=$(CPP_BASE)/3rdparty/$(PROTO_NAME)/$(BUILDDIR)/$(PROTO_NAME)
PROTO_INC=-I$(PROTO_BASE)/src
PROTO_LIB=-L$(PROTO_BASE)/src/.libs -lprotobuf
PROTOC=$(CPP_BASE)/3rdparty/$(PROTO_NAME)/$(BUILDDIR)/$(PROTO_NAME)/src/protoc

#JSONCPP_BASE=$(CPP_BASE)/3rdparty/jsoncpp-20141023
JSONCPP_BASE=$(CPP_BASE)/3rdparty/jsoncpp-1.8.3
JSONCPP_INC=-I$(JSONCPP_BASE)/include
#JSONCPP_LIB=-L$(JSONCPP_BASE)/build/lib -ljsoncpp
JSONCPP_LIB=-L$(JSONCPP_BASE)/build/src/lib_json -ljsoncpp

B64_BASE=$(CPP_BASE)/3rdparty/libb64-1.2.1
B64_INC=-I$(B64_BASE)/include
B64_LIB=$(B64_BASE)/src/libb64.a

CXXFLAGS=$(PROTO_INC) $(JSONCPP_INC) $(B64_INC)
LDFLAGS=$(PROTO_LIB) $(JSONCPP_LIB) $(B64_LIB)

LIB_NAME=libjson_protobuf
LIB=$(LIB_NAME).so
ARCHIVE=$(LIB_NAME).a

TEST_PROG=check_json_protobuf
TEST_PROTO_NAME=check_protobuf_types
TEST_PROTO_FILE=$(TEST_PROTO_NAME).proto
TEST_PROTO_SRC=$(TEST_PROTO_NAME).pb.cc
TEST_PROG_SRCS=$(TEST_PROG).cpp $(TEST_PROTO_SRC)

OBJS=json_protobuf.o

all: $(LIB) $(ARCHIVE)

$(ARCHIVE): $(OBJS)
	$(AR) cr $@ $^

$(LIB): $(OBJS)
	${CXX} ${CXXFLAGS} $(LDFLAGS) $^ -shared -o $@

%.o: %.cpp
	${CXX} ${CXXFLAGS} -c -fPIC $< -o $@

$(TEST_PROTO_SRC): $(TEST_PROTO_FILE)
	${PROTOC} --cpp_out=. $<

$(TEST_PROG): $(TEST_PROG_SRCS) $(ARCHIVE)
	${CXX} ${CXXFLAGS} $^ \
		$(ARCHIVE) \
		-o $@ ${LDFLAGS} 

test: $(TEST_PROG)
	./check_json_protobuf

clean:
	rm -rf $(LIB) $(ARCHIVE) $(TEST_PROG) *.pb.* *.o

env:
	echo "PROTO_NAME=$(PROTO_NAME)"

include ../../../../util/include.mk
