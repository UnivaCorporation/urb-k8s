#!/usr/bin/env python

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


import platform
import sys
import subprocess
import os
import threading
from optparse import OptionParser

DEFAULT_HOSTFILE='./hostfile'
DEFAULT_TIMEOUT=5

this_script_full = os.path.abspath(__file__)
this_script_base = './' + os.path.basename(__file__)

def check_cpu(f):
    """ Decorator for use with the WhatOS class; checks cpu_support instance
    variable and returns False if the value of cpu_supported is False.
    Otherwise executes decorated function.
    """
    def new_f(self, *args, **kwargs):
        if self.cpu_supported:
            return f(self, *args, **kwargs)
        else:
            return False
    return new_f
            
class WhatOS():
    """ Determine OS-type and version of the system we run on and whether we
    run on a system that is supported.

    Only x86 systems are supported. All methods will return False if we are on
    another platform.

    On supported CPU platforms, the following methods are available:
        linux:   determine OS-type and version for (some) Linux distros
        solaris: determine OS-type and version for Solaris distros
        macos:   determine OS-type and version for Mac OS X distros
        any:     check whether we are on Linux, Solaris or MacOS and run the
                 corresponding method above
    In all cases, expect the following results:
        self.ostype:  contains determined OS-type or self.NOSUPPORT
        self.version: contains determined major version number or self.ERRORVERS
        True will be returned if self.ostype and self.version were determined
            successfully. Otherwise False will be returned

    Change the below class variables to modify the set of supported OS
    platforms. You may also need to modify the os_class_map instance variable
    (see __init__()) and add or modify an instance method.
    """
    # String constants representing "not found" for OS-type and version
    NOSUPPORT = 'not_supported'
    ERRORVERS = 'error_version'

    # All os type strings we may store in self.ostype in the end
    RH_OSTYPE      = 'redhat'
    SUSE_OSTYPE    = 'suse'
    UBUNTU_OSTYPE  = 'ubuntu'
    SOLARIS_OSTYPE = 'solaris'
    MACOS_OSTYPE   = 'darwin'

    # Linux os type strings being recognized as displayed by 1st elem of platform.dist()
    RH_OS_STRS     = [ 'redhat', 'centos' ]
    SUSE_OS_STRS   = [ 'SuSE' ]
    UBUNTU_OS_STRS = [ 'Ubuntu' ]

    # Use a dict for Linux to map recognized platform.dist()[0] strings vs ostypes
    # Used in self.linux() method
    LX_OSTYPE_MAP = {}
    for e in RH_OS_STRS:
        LX_OSTYPE_MAP[e] = RH_OSTYPE
    for e in SUSE_OS_STRS:
        LX_OSTYPE_MAP[e] = SUSE_OSTYPE
    for e in UBUNTU_OS_STRS:
        LX_OSTYPE_MAP[e] = UBUNTU_OSTYPE

    # Supported OS class string as returned by plaform.system()
    LINUX_CLASS   = 'Linux'
    SOLARIS_CLASS = 'SunOS'
    MACOS_CLASS   = 'Darwin'

    # Supported CPU platforms
    SUPPORTED_CPU_TYPES = [ 'x86_64', 'i386', 'i686' ]

    def __init__(self):
        """ AnyOS instance creation """
        # self.ostype and self.version are intended to store the results of
        # running the methods of this class
        # Set "not found" as default
        self.ostype  = self.NOSUPPORT
        self.version = self.ERRORVERS

        # Store results of the platform module methods we use in instance vars
        self.dist      = platform.dist()
        self.system    = platform.system()
        self.platform  = platform.platform()
        self.uname     = platform.uname()

        # Check whether we are running on a CPU arch being supported currently
        # The CPU arch is the last element in platform.uname()
        self.cpu_supported = self.uname[-1] in WhatOS.SUPPORTED_CPU_TYPES

        # Method map for OS classes; keys correspond to output of platform.system()
        self.os_class_map = {
            WhatOS.LINUX_CLASS:   self.linux,
            WhatOS.SOLARIS_CLASS: self.solaris,
            WhatOS.MACOS_CLASS:   self.macos,
        }

    @check_cpu
    def linux(self):
        """ Find Linux OS-type and major OS version """
        os = WhatOS.LX_OSTYPE_MAP.get(self.dist[0])
        if os:
            self.ostype = os

        # Use try clause in case there is something odd with format of info in
        # self.dist, i.e. platform.dist()
        try:
            # 2nd entry on platform.dist() on Linux is '<MajorVers>[.*]'
            # We need <MajorVers> so all before 1st '.' if present
            idx = self.dist[1].find('.')
            if idx == -1:
                self.version = self.dist[1]
            else:
                self.version = self.dist[1][:idx]
        except:
            pass

    @check_cpu
    def solaris(self):
        """ Find Solaris OS-type and major OS version """
        self.ostype = WhatOS.SOLARIS_OSTYPE
        try:
            # 3rd entry to platform.uname() on Solaris is '5.<MajorVers>'
            # We need <MajorVers>, so after the first '.'
            self.version = self.uname[2][self.uname[2].find('.')+1:]
        except:
            pass

    @check_cpu
    def macos(self):
        """ Find MacOS OS-type and major OS version """
        self.ostype = WhatOS.MACOS_OSTYPE
        try:
            # platform.platform() on MacOS is 'Darwin-<MajorVers>.*'
            # We need <MajorVers>, so between the first '-' and the first '.'
            self.version = self.platform[self.platform.find('-')+1:self.platform.find('.')]
        except:
            pass

    @check_cpu
    def any(self):
        """ Determine whether we are on Linux, SunOS or Darwin and then get
        the OS-type and major OS version
        """
        self.os_class_map[self.system]()
        if self.ostype == WhatOS.NOSUPPORT or self.version == WhatOS.ERRORVERS:
            return False

class ProcessTimeoutException(Exception):
    pass

class PopenWithTimeout(object):
    """Class for making subprocess calls with timeouts."""
    def __init__(self, cmd):
        self.cmd = cmd
        self.process = None
        self.stdout = None
        self.stderr = None
        self.returncode = None

    def communicate(self, timeout):
        def run_subprocess(self):
            try:
                self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.stdout, self.stderr = self.process.communicate()
                self.returncode = self.process.returncode
            except Exception as e:
                self.stderr = str(sys.exc_traceback)
                self.returncode = 111

        thread = threading.Thread(target=run_subprocess, args=(self,))
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            self.process.terminate()
            raise ProcessTimeoutException()

        return self.stdout, self.stderr

def get_cluster_arch_map(hostlist=None, method='qrsh', timeout=DEFAULT_TIMEOUT):
    """ Get map of OS distribution strings vs hosts on a list of hosts """
    archd = {}

    for h in hostlist:
        # Get OS distribution string of a single host
        arch = arch_of_host(host=h, method=method, timeout=timeout)

        # Skip hosts with no result, e.g. due to a timeout
        if not arch:
            continue
        
        # Keys are OS distribution strings and values are lists of corresponding hosts
        if arch in archd.keys():
            archd[arch].append(h)
        else:
            archd[arch] = [ h ]

    return archd

def arch_of_host(host=None, method='qrsh', timeout=DEFAULT_TIMEOUT):
    """ Determine OS distribution string via remote execution of this script
    itself without arguments on a given host
    """
    if not host:
        return ''

    # Assemble remote execution command in list
    if method == 'qrsh':
        # Using -cwd and base script path for qrsh; that way some scenrios
        # with links and such might still work
        cmdl = [ 'qrsh', '-noshell', '-cwd', '-l', 'h=' + host, this_script_base ]
    else:
        cmdl  = [ 'ssh', host, this_script_full ]

    # Run the command with timeout
    p = PopenWithTimeout(cmdl)
    try:
        so, se = p.communicate(timeout)
    except ProcessTimeoutException:
        # We just skip hosts where we got an exception by returning an empty
        # string
        return ''
    if so:
        # Make sure there is no '\n' at the end of the OS distribution string
        so = so.split()[0]

    return so

def get_exechost_list(timeout=DEFAULT_TIMEOUT):
    """ Get exec host list via Grid Engine command qconf -sel
    """
    cmdl = [ 'qconf', '-sel' ]
    p = PopenWithTimeout(cmdl)
    try:
        so, se = p.communicate(timeout)
    except ProcessTimeoutException:
        return ''
    return so.split()

def read_host_file(fname=DEFAULT_HOSTFILE):
    """ Get host list from file
    """
    with open(fname, 'r') as f:
        return f.read().split()
    
def parse_cli_opts():
    """ CLI option parser """
    usage = """ %prog [options]

Determines OS distribution string for one host or all hosts in a cluster. An
OS distribution string is the category of OS distribution (e.g. 'redhat' is
used for RHEL and CentOS) with a '_' and the major OS version number being
appended (e.g. 'redhat_6' for 'RHEL 6.6' or 'CentOS 6.2' and so on).

With the --all or --map options %prog determins the unique OS distribution
strings for all hosts in a cluster. Per default it uses 'qconf -sel' to get a
list of all hosts and then 'qrsh' to run the check. For this to work you have
to have Grid Engine settings sourced. Alternatively you can supply a file with
host names (one per line) and 'ssh' for remote execution of the check.

In both cases for %prog to work you either need to have this script reside in
a directory on a shared filesystem or you copy this script to a location with
the same path name on all hosts of the cluster.

Remote execution times out after 5 seconds per default. Increase it if remote
execution per host may take longer in your case (e.g. because you need to
enter passwords in case of ssh or because dispatching qrsh jobs can take
longer).

If you run %prog without options then it will just display the OS distribution
string of the host you run it on.
"""

    parser = OptionParser(usage=usage)

    parser.add_option('-a', '--all', dest='doall', action='store_true',
        help='Print list of architecture strings in cluster')
    parser.add_option('-f', '--host-file', dest='hostfilename', action='store',
        type='string', help='Read hostnames from FILE; uses qconf -sel if absent.',
        metavar='FILE')
    parser.add_option('-m', '--map', dest='dofull', action='store_true',
        help='Same as --all but print map of architecture strings and hosts')
    parser.add_option('-r', '--remote-exec', dest='method', action='store',
        type='string', help='Remote execution method - qrsh (Default) or ssh.',
        default='qrsh', metavar='RCMD')
    parser.add_option('-t', '--timeout', dest='timeout', action='store',
        type='int', default=DEFAULT_TIMEOUT,
        help='Timeout for qrsh and ssh calls. Default 5s.')

    return parser.parse_args()

if __name__ == '__main__':
    # See 'usage' string in parse_cli_opts() for what the module does when
    # used standalone

    # Parse CLI options
    options, args = parse_cli_opts()

    # Two principle modes:
    # - options.doall or options.dofull is True: determine OS string for all hosts
    #       ==> script will run itself on hosts via qrsh or ssh
    # - otherwise: determine OS string for local host only

    if options.doall or options.dofull:
        # do it for all ==> get host list, either via host file or qconf -sel (default)
        if options.hostfilename:
            hlist = read_host_file(options.hostfilename)
        else:
            hlist = get_exechost_list(timeout=options.timeout)

        # Get architecture map ==> dict with OS strings as key and list of
        # corresponding host names as value
        arch_map = get_cluster_arch_map(hlist, method=options.method,
            timeout=options.timeout)

        # Print full map or just list of OS strings
        if options.dofull:
            for k, v in arch_map.items():
                print(k + ':', ' '.join(v))
        else:
            print('\n'.join(arch_map.keys()))

        # Ignore all errors and timeouts. Errors in determining OS strings
        # will show up as "not supported". Hosts with timeout will get
        # skipped.

    else:
        # only run it on local host (mode used when launched via qrsh or ssh
        # on remote host)
        os = WhatOS()
        ret = os.any()
        print(os.ostype + '_' + os.version)

        # Provide exit status in case of errors but suppress if called inside
        # of a Grid Engine job to avoid clobbering of faulty_jobs directory
        if ret and not os.environ.get('JOB_ID'):
            sys.exit(1)
