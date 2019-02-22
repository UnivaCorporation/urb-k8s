#project('liburb', ['cpp', 'java'], cpp_std : 'c++11')
src = [
  'source/attributes.cpp',
  'source/construct.cpp',
  'source/convert.cpp',
  'source/evhelper.cpp',
  'source/exec.cpp',
  'source/executor_process.cpp',
  'source/lock.cpp',
  'source/message_broker.cpp',
  'source/message_broker_redis.cpp',
  'source/messages.cpp',
  'source/org_apache_mesos_MesosExecutorDriver.cpp',
  'source/org_apache_mesos_MesosNativeLibrary.cpp',
  'source/org_apache_mesos_MesosSchedulerDriver.cpp',
  'source/resources.cpp',
  'source/resources_utils.cpp',
  'source/roles.cpp',
  'source/sched.cpp',
  'source/scheduler_process.cpp',
  'source/type_utils.cpp',
  'source/values.cpp'
]
dep = dependency('zlib')
thread_dep = dependency('threads')
#gtest_dep = dependency('gtest')
#javadep = dependency('openjdk')
java_inc = include_directories(['/etc/alternatives/java_sdk/include', '/etc/alternatives/java_sdk/include/linux'])
mesos_inc = include_directories(['mesos/include', 'mesos/include/mesos'])
liburb_dep = deps_3rdparty
#message(liburb_dep)
liburb_dep += thread_dep
liburb_inc = [ java_inc, mesos_inc ]
#liburb_inc += mesos_inc
lib = shared_library('liburb',
  src,
  dependencies : [ liburb_dep ],
  include_directories : liburb_inc,
  version : meson.project_version()
)

  # 'source/concurrent_queue.hpp
  # 'source/construct.hpp
  # 'source/convert.hpp
  # 'source/evhelper.hpp
  # 'source/executor_process.hpp
  # 'source/message_broker.hpp
  # 'source/message_broker_redis.hpp
  # 'source/org_apache_mesos_MesosExecutorDriver.h
  # 'source/org_apache_mesos_MesosSchedulerDriver.h
  # 'source/scheduler_process.hpp
  # 'source/timer.hpp
  # 'source/url.hpp
