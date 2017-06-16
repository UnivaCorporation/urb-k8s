# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import errno
import glob
import os
import shutil
import sys

from setuptools import Extension

def _create_module_0(module_name):
    abs_top_srcdir = '/vagrant/mesos/mesos-1.1.0/build/..'
    abs_top_builddir = '/vagrant/mesos/mesos-1.1.0/build'

    ext_src_dir = os.path.join(
        'src', 'python', module_name, 'src', 'mesos', module_name)
    ext_common_dir = os.path.join(
        'src', 'python', 'native_common')

    leveldb = os.path.join('3rdparty', 'leveldb-1.4')
    zookeeper = os.path.join('3rdparty', 'zookeeper-3.4.8', 'src', 'c')
    libprocess = os.path.join('3rdparty', 'libprocess')

    # Even though a statically compiled libprocess should include glog,
    # libev, gperftools, and protobuf before installation this isn't the
    # case, so while a libtool managed build will correctly pull in these
    # libraries when building the final result, we need to explicitly
    # include them here (or more precisely, down where we actually include
    # libev.a and libprofiler.a).
    glog = os.path.join('3rdparty', 'glog-0.3.3')
    gperftools = os.path.join('3rdparty', 'gperftools-2.5')
    protobuf = os.path.join('3rdparty', 'protobuf-2.6.1')

    # Build the list of source files. Note that each source must be
    # relative to our current directory (where this script lives).
    SOURCES = [
        os.path.join('src', 'mesos', module_name, file)
            for file in os.listdir(os.path.join(abs_top_srcdir, ext_src_dir))
                if file.endswith('.cpp')
    ]

    INCLUDE_DIRS = [
        os.path.join(abs_top_srcdir, 'include'),
        os.path.join(abs_top_builddir, 'include'),
        # Needed for the *.pb.h protobuf includes.
        os.path.join(abs_top_builddir, 'include', 'mesos'),
        os.path.join(abs_top_builddir, 'src'),
        os.path.join(abs_top_builddir, ext_src_dir),
        os.path.join(abs_top_builddir, ext_common_dir),
        os.path.join(abs_top_builddir, protobuf, 'src'),
    ]

    LIBRARY_DIRS = []

    EXTRA_OBJECTS = [
        os.path.join(abs_top_builddir, 'src', '.libs', 'libmesos_no_3rdparty.a'),
        os.path.join(abs_top_builddir, libprocess, '.libs', 'libprocess.a')
    ]

    # For leveldb, we need to check for the presence of libleveldb.a, since
    # it is possible to disable leveldb inside mesos.
    libglog = os.path.join(abs_top_builddir, glog, '.libs', 'libglog.a')
    libleveldb = os.path.join(abs_top_builddir, leveldb, 'libleveldb.a')
    libzookeeper = os.path.join(
        abs_top_builddir, zookeeper, '.libs', 'libzookeeper_mt.a')
    libprotobuf = os.path.join(
        abs_top_builddir, protobuf, 'src', '.libs', 'libprotobuf.a')

    if os.path.exists(libleveldb):
        EXTRA_OBJECTS.append(libleveldb)
    else:
        EXTRA_OBJECTS.append('-lleveldb')

    if os.path.exists(libzookeeper):
        EXTRA_OBJECTS.append(libzookeeper)
    else:
        EXTRA_OBJECTS.append('-lzookeeper_mt')

    if os.path.exists(libglog):
        EXTRA_OBJECTS.append(libglog)
    else:
        EXTRA_OBJECTS.append('-lglog')

    if os.path.exists(libprotobuf):
      EXTRA_OBJECTS.append(libprotobuf)
    else:
      EXTRA_OBJECTS.append('-lprotobuf')


    # libev is a special case because it needs to be enabled only when
    # libevent *is not* enabled through the top level ./configure.
    #
    # TODO(hartem): this entire block MUST be removed once libev is deprecated
    # in favor of libevent.
    if '#' == '#':
        libev = os.path.join('3rdparty', 'libev-4.22')
        libev = os.path.join(abs_top_builddir, libev, '.libs', 'libev.a')

        if os.path.exists(libev):
            EXTRA_OBJECTS.append(libev)
        else:
            EXTRA_OBJECTS.append('-lev')


    # For gperftools, we need to check for the presence of libprofiler.a, since
    # it is possible to disable perftools inside libprocess.
    libprofiler = os.path.join(
        abs_top_builddir, gperftools, '.libs', 'libprofiler.a')

    if os.path.exists(libprofiler):
        EXTRA_OBJECTS.append(libprofiler)

    # OSX uses a different linker (llvm-ld) and doesn't support --as-needed
    # TODO(SteveNiemitz): Feature detect --as-needed instead of looking at
    # sys.platform.
    EXTRA_LINK_ARGS = ['-Wl,--as-needed'] if sys.platform != 'darwin' else []

    # Add any flags from LDFLAGS.
    if 'LDFLAGS' in os.environ:
        for flag in os.environ['LDFLAGS'].split():
            EXTRA_LINK_ARGS.append(flag)

    # Add any libraries from LIBS.
    if 'LIBS' in os.environ:
        for library in os.environ['LIBS'].split():
            EXTRA_LINK_ARGS.append(library)

    # Note that we add EXTRA_OBJECTS to our dependency list to make sure
    # that we rebuild this module when one of them changes (e.g.,
    # libprocess).
    mesos_module = \
        Extension('mesos.%s._%s' % (module_name, module_name),
                  sources = SOURCES,
                  include_dirs = INCLUDE_DIRS,
                  library_dirs = LIBRARY_DIRS,
                  extra_objects = EXTRA_OBJECTS,
                  extra_link_args = EXTRA_LINK_ARGS,
                  depends = EXTRA_OBJECTS,
                  language = 'c++',
                  )
    return mesos_module

def _create_module(module_name):
  print "Create module %s" % module_name
  abs_top_srcdir = os.getcwd()
  print 'abs_top_srcdir: %s' % abs_top_srcdir
  #abs_top_builddir = os.getcwd()
  abs_top_builddir = os.path.join(os.getcwd(), '../', 'build')
  print 'abs_top_builddir: %s' % abs_top_builddir

  common_dir = os.path.join(abs_top_srcdir, '..', 'native_common')

  #src_python_native = os.path.join(
  #    'src', 'python', 'native', 'src', 'mesos', 'native')
  src_python = os.path.join('src', 'mesos', module_name)
  print 'src_python: %s' % src_python

  for file in os.listdir(os.path.join(abs_top_srcdir, src_python)):
      print "%s" % file
 
  SOURCES = [
      os.path.join(abs_top_srcdir, 'src', 'mesos', module_name, file)
          for file in os.listdir(os.path.join(abs_top_srcdir, src_python))
              if file.endswith('.cpp')
  ]
  print "SOURCES: %s" % SOURCES

  print "URB_PYTHON_INCLUDE: %s: " % os.environ.get("URB_PYTHON_INCLUDE","-Idummy")
  INCLUDE_DIRS = [ i[2:] for i in os.environ.get("URB_PYTHON_INCLUDE","-Idummy").split(" ") ]
  INCLUDE_DIRS.append(common_dir)
  print "INCLUDE_DIRS: %s" % INCLUDE_DIRS
  LIBRARY_DIRS = []

  EXTRA_OBJECTS = [
    o for o in os.environ.get("URB_PYTHON_OBJECTS","").split(" ")
  ]

  EXTRA_LINK_ARGS = []

  # Add any flags from LDFLAGS.
  if 'LDFLAGS' in os.environ:
      for flag in os.environ['LDFLAGS'].split():
          EXTRA_LINK_ARGS.append(flag)

  # Add any libraries from LIBS.
  if 'LIBS' in os.environ:
      for library in os.environ['LIBS'].split():
          EXTRA_LINK_ARGS.append(library)


  EXTRA_COMPILE_ARGS = []

  if 'CFLAGS' in os.environ:
      for cflag in os.environ['CFLAGS'].split():
          EXTRA_COMPILE_ARGS.append(cflag)

  # Note that we add EXTRA_OBJECTS to our dependency list to make sure
  # that we rebuild this module when one of them changes (e.g.,
  # libprocess).
  mesos_module = \
      Extension('mesos.%s._%s' % (module_name, module_name),
                sources = SOURCES,
                include_dirs = INCLUDE_DIRS,
                library_dirs = LIBRARY_DIRS,
                extra_objects = EXTRA_OBJECTS,
                extra_link_args = EXTRA_LINK_ARGS,
                depends = EXTRA_OBJECTS,
                language = 'c++',
                )
  return mesos_module

#executor_module = _create_module("executor")
#scheduler_module = _create_module("scheduler")
