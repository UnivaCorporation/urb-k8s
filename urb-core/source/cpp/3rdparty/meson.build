run_command('make', '-C', meson.current_source_dir(), check : true)

glog_inc = include_directories(['glog-0.3.3/build/src', 'glog-0.3.3/src'])
#glog_lib = meson.get_compiler('cpp').find_library('glog', dirs : join_paths(meson.current_build_dir(), 'glog-0.3.3/build/.libs'))
#glog_lib = static_library('libglog.a')
#glog_lib = static_library('glog-0.3.3/build/.libs/libglog.a')
glog_dep = declare_dependency(
#  link_with : glog_lib,
  include_directories : glog_inc
)
deps_3rdparty += glog_dep

protobuf_inc = include_directories(['protobuf-3.3.0/build/src'])
#protobuf_lib = 
protobuf_dep - declare_dependency(
#  link_with : protobuf_lib,
  include_directories : protobuf_inc
)
deps_3rdparty += protobuf_dep

