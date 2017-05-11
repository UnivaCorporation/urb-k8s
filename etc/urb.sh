#!/bin/bash

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




