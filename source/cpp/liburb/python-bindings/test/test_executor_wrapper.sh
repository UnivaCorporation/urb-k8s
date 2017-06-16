#!/bin/bash
#######################################################################
##                                                                   ##
##   Copyright (c) 2014, Univa.  All rights reserved.                ##
##   http://www.univa.com                                            ##
##                                                                   ##
##   License:                                                        ##
##     Univa                                                         ##
##                                                                   ##
##                                                                   ##
#######################################################################

# Simple shell script to make sure the mesos module is available for the executor
cd `dirname $0`

source ../dist/testpy/bin/activate
exec ./test_executor.py "$@"
