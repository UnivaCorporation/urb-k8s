libprocess was added during URB upgrade to mesos 0.22.0 to satisfy dependency from 'fetcher'
which required 'logging' which required using once.hpp
only include part of libprocess library added here since no compilation needed to use 'once'
