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

require epel

class { 'java': }

package { 'gcc-c++':
  ensure => 'installed',
}

package { 'make':
  ensure => 'installed',
}

package { 'cmake':
  ensure => 'installed',
}

package { 'wget':
  ensure => 'installed',
}

package { 'rsync':
  ensure => 'installed',
}

package { 'less':
  ensure => 'installed',
}

package { 'file':
  ensure => 'installed',
}

package { 'patch':
  ensure => 'installed',
}

package { 'unzip':
  ensure => 'installed',
}

package { 'libcurl-devel':
  ensure => 'installed',
}

package { 'msgpack-devel':
  ensure => 'installed',
}

package { 'libev-devel':
  ensure => 'installed',
}

package { 'libuuid-devel':
  ensure => 'installed',
}

package { "python-setuptools":
  ensure => "installed"
}

package { "python-virtualenv":
  ensure => "installed"
}

package { "python-pip":
  ensure => "installed"
}

package { "zlib-devel":
  ensure => "installed"
}

exec { "install_nose":
   unless => "/usr/bin/env python -c 'import nosexcover'",
   command => "/usr/bin/easy_install nosexcover",
   require => Package['python-setuptools']
}

exec { "install_pylint":
   unless => "/usr/bin/env python -c 'import pylint'",
   command => "/usr/bin/easy_install pylint",
   require => Package['python-setuptools']
}

# choosing version 1.0.1 since latest versions require more up-to-date setuptools
exec { "install_mock":
   unless => "/usr/bin/env python -c 'import mock'",
   command => "/usr/bin/easy_install mock==1.0.1",
   require => Package['python-setuptools']
}

# set stable version for now (to avoid latest 1.3a1)
exec { "install_gevent":
   unless => "/usr/bin/env python -c 'import gevent'",
   command => "/usr/bin/easy_install gevent==1.2.2",
   timeout => 600,
   require => Package['python-setuptools']
}

exec { "install_pymongo":
   unless => "/usr/bin/env python -c 'import pymongo'",
   command => "/usr/bin/easy_install pymongo",
   timeout => 600,
   require => Package['python-setuptools']
}

exec { "install_sortedcontainers":
   unless => "/usr/bin/env python -c 'import sortedcontainers'",
   command => "/usr/bin/easy_install sortedcontainers",
   timeout => 600,
   require => Package['python-setuptools']
}

exec { "install_xmltodict":
   unless => "/usr/bin/env python -c 'import xmltodict'",
   command => "/usr/bin/easy_install xmltodict",
   timeout => 600,
   require => Package['python-setuptools']
}

exec { "install_gevent_inotifyx":
   unless => "/usr/bin/env python -c 'import gevent_inotifyx'",
   command => "/usr/bin/easy_install gevent_inotifyx",
   timeout => 600,
   require => Package['python-setuptools']
}

exec { "install_redis":
   unless => "/usr/bin/env python -c 'import redis'",
   command => "/usr/bin/easy_install redis",
   timeout => 600,
   require => Package['python-setuptools']
}

exec { "remove_hosts":
   command => "/bin/echo '127.0.0.1 localhost localhost.localdomain' >> /etc/hosts",
   unless => "/bin/grep $::ipaddress /etc/hosts",
}

host { 'head.private':
    host_aliases => 'head',
    ip => $::ipaddress,
    ensure => 'present',
    require => Exec["remove_hosts"]
}
