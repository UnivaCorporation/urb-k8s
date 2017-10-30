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

set -x

if [ ! -z "$VERSION" ]; then
  VERSION_PARAM="VERSION=$VERSION"
fi
if [ ! -z "$FULL_MESOS_LIB" ]; then
  FULL_MESOS_LIB_PARAM="FULL_MESOS_LIB=1"
fi
if [ ! -z $STOCK_MESOS_DIR ]; then
  STOCK_MESOS_DIR_PARAM="STOCK_MESOS_DIR=$STOCK_MESOS_DIR"
fi

# remove docker image
rmi() {
  local nm=$1
  # add space to get unique name
  local img=$(docker images | awk "/$nm / {print \$3}")
  if [ ! -z "$img" ]; then
    local containers=$(docker ps -a | awk "/$img/ {print \$1}")
    if [ ! -z "$containers" ]; then
      docker rm $containers
      local containers_left=$(docker ps -a | awk "/$img/ {print \$1}")
      if [ ! -z "$containers_left" ]; then
        set -e
        docker rm -f $containers_left
        set +e
      fi
    fi
    docker rmi $img
    if [ $? -ne 0 ]; then
      docker rmi -f $img
      if [ $? -ne 0 ]; then
        rmi_dep $img
      fi
    fi
  fi
}

# remove <none> docker images
rmi_none() {
  im=$(docker images | awk "/^<none>/ {print \$3}")
  if [ ! -z "$im" ]; then
    docker rmi $im
    if [ $? -ne 0 ]; then
      set -e
      docker rmi -f $(docker images | awk "/^<none>/ {print \$3}")
      set +e
    fi
  fi
}

rmi_dep() {
  local im=$1
  for ii in $(docker images -q); do
    if docker history $ii | grep -q $im; then
      docker rmi $ii
      if [ $? -ne 0 ]; then
        docker rmi -f $ii
      fi
    fi
  done
}

# set minikube docker environment
set_minikube_env() {
  eval $(minikube docker-env)
}

# clear minikube docker environment
clear_minikube_env() {
  unset DOCKER_HOST
  unset DOCKER_API_VERSION
  unset DOCKER_TLS_VERIFY
  unset DOCKER_CERT_PATH
}

# delete k8s objects by type and pattern
delete_wait() {
  local obj=$1
  local pattern=$2
  local list=$(kubectl get $obj -a | awk "/$pattern/ {print \$1}")
  if [ ! -z "$list" ]; then
    kubectl delete $obj $list
    cnt_max=20
    cnt=0
    while [ $cnt -le $cnt_max ]; do
      if ! kubectl get $obj -a | grep $pattern ; then
        break
      fi
      cnt=$((cnt+1))
      sleep 1
    done
    if [ $cnt -ge $cnt_max ]; then
      echo "WARNING: not all $obj $pattern were deleted within $cnt_max sec"
    fi
  fi
}
if [ $# -eq 0 ]; then
  URB_SERVICE=1
  URB_REDIS=1
  URB_EXECUTOR_RUNNER=1
  CPP_EXAMPLE=1
  PYTHON_EXAMPLE=1
  URB_BIN_BASE=1
  URB_PYTHON_BASE=1
else
  while [ $# -gt 0 ]; do
    case "$1" in
    "urb-service")
      URB_SERVICE=1
      shift
      ;;
    "urb-redis")
      URB_REDIS=1
      shift
      ;;
    "urb-executor-runner")
      URB_EXECUTOR_RUNNER=1
      shift
      ;;
    "cpp-framework")
      CPP_EXAMPLE=1
      shift
      ;;
    "python-framework")
      PYTHON_EXAMPLE=1
      shift
      ;;
    "urb-bin-base")
      URB_BIN_BASE=1
      shift
      ;;
    "urb-python-base")
      URB_PYTHON_BASE=1
      shift
      ;;
    *)
    ;;
    esac
  done
fi

set_minikube_env

# clean
kubectl delete job cpp-framework python-framework urb-exec spark spark-driver
kubectl delete deployment,service urb-master marathonsvc
delete_wait jobs urb-exec
kubectl get pods -a
delete_wait pods urb-exec

rmi "local\/spark"
rmi "local\/spark-driver"
if [ ! -z "$URB_SERVICE" ]; then
  rmi "local\/urb-service"
fi
if [ ! -z "$URB_REDIS" ]; then
  rmi "local\/urb-redis"
fi
if [ ! -z "$CPP_EXAMPLE" ]; then
  rmi "local\/cpp-framework"
fi
if [ ! -z "$PYTHON_EXAMPLE" ]; then
  rmi "local\/python-framework"
  rmi "local\/python-executor-runner"
fi
if [ ! -z "$URB_EXECUTOR_RUNNER" ]; then
  rmi "local\/urb-executor-runner"
fi
if [ ! -z "$URB_BIN_BASE" ]; then
  rmi "local\/urb-bin-base"
fi
if [ ! -z "$URB_PYTHON_BASE" ]; then
  rmi "local\/urb-python-base"
fi
rmi_none

# rebuild URB artifacts
clear_minikube_env
pushd urb-core/vagrant
set -e
SYNCED_FOLDER=../.. vagrant ssh -- "cd /scratch/urb; rm -rf source/python/build source/python/dist urb-core/dist urb-core/source/python/dist urb-core/source/python/build && $STOCK_MESOS_DIR_PARAM $FULL_MESOS_LIB_PARAM $VERSION_PARAM make && $STOCK_MESOS_DIR_PARAM $FULL_MESOS_LIB_PARAM $VERSION_PARAM make dist"
set +e
popd

# create docker images
set_minikube_env

if [ ! -z "$URB_SERVICE" ]; then
  make urb-service
fi
if [ ! -z "$URB_REDIS" ]; then
  make urb-redis
fi
if [ ! -z "$CPP_EXAMPLE" ]; then
  make cpp-framework
fi
if [ ! -z "$PYTHON_EXAMPLE" ]; then
  make python-framework python-executor-runner
fi
if [ ! -z "$URB_EXECUTOR_RUNNER" ]; then
  make urb-executor-runner
fi
if [ ! -z "$URB_BIN_BASE" ]; then
  make urb-bin-base
fi
if [ ! -z "$URB_PYTHON_BASE" ]; then
  make urb-python-base
fi

# create URB configuration
kubectl create configmap urb-config --from-file=etc/urb.conf --dry-run -o yaml | kubectl replace -f -
# start URB master
kubectl create -f source/urb-master.yaml
kubectl get pods

