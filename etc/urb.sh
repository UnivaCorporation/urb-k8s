#!/bin/bash
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

# URB environment setup file.

CURRENT_DIR=`pwd`
MY_DIR=`dirname $BASH_SOURCE` && cd $MY_DIR && MY_DIR=`pwd`
if [ -z $URB_ROOT ]; then
    cd $MY_DIR/.. && URB_ROOT=`pwd`
fi
export URB_ROOT

# config file
if [ -z $URB_CONFIG_FILE ]; then
    export URB_CONFIG_FILE=$MY_DIR/urb.conf
fi

# python path
if [ -z $PYTHONPATH ]; then
    PYTHONPATH=.:$URB_ROOT/source/python
else
    PYTHONPATH=.:$URB_ROOT/source/python:$PYTHONPATH
fi
export PYTHONPATH
cd $CURRENT_DIR




