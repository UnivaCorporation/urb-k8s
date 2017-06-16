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


import os
import shutil

from setuptools import Extension

abs_top_srcdir = os.getcwd()
print 'abs_top_srcdir: %s' % abs_top_srcdir
#abs_top_builddir = os.getcwd()
abs_top_builddir = os.path.join(os.getcwd(), '../', 'build')
print 'abs_top_builddir: %s' % abs_top_builddir

#src_python_native = os.path.join(
#    'src', 'python', 'native', 'src', 'mesos', 'native')
src_python_native = os.path.join(
    'src', 'mesos', 'native')
print 'src_python_native: %s' % src_python_native

SOURCES = [
    os.path.join('src', 'mesos', 'native', file)
        for file in os.listdir(os.path.join(abs_top_srcdir, src_python_native))
            if file.endswith('.cpp')
]
print "URB_PYTHON_INCLUDE: %s: " % os.environ.get("URB_PYTHON_INCLUDE","-Idummy")
INCLUDE_DIRS = [ i[2:] for i in os.environ.get("URB_PYTHON_INCLUDE","-Idummy").split(" ") ]
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
    Extension('mesos.native._mesos',
              sources = SOURCES,
              include_dirs = INCLUDE_DIRS,
              library_dirs = LIBRARY_DIRS,
              extra_objects = EXTRA_OBJECTS,
              extra_link_args = EXTRA_LINK_ARGS,
              extra_compile_args = EXTRA_COMPILE_ARGS,
              depends = EXTRA_OBJECTS,
              language = 'c++',
              )


if os.environ.get('USER','') == 'vagrant':
    del os.link

mesos_version= os.environ.get('EXT_MESOS_VERSION', '0.22.0')

config = {
    'name': 'mesos.native',
    'version': mesos_version,
    'description': 'Mesos native driver implementation',
    'author': 'Apache Mesos',
    'author_email': 'dev@mesos.apache.org',
    'url': 'http://pypi.python.org/pypi/mesos.native',
    'namespace_packages': [ 'mesos' ],
    'packages': [ 'mesos', 'mesos.native' ],
    'package_dir': { '': 'src' },
    'install_requires': [ 'mesos.interface == ' + mesos_version ],
    'license': 'Apache 2.0',
    'keywords': 'mesos',
    'classifiers': [ ],
    'ext_modules': [ mesos_module ]
}

from setuptools import setup

setup(**config)
