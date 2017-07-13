#!/bin/bash
set -x

rmi() {
  local nm=$1
  local img=$(docker images | awk "/$nm/ {print \$3}")
  local containers=$(docker ps -a | awk "/$img/ {print \$1}")
  if [ ! -z "$containers" ]; then
    docker rm $containers  
  fi
  docker rmi $img
}

rmi_none() {
  docker rmi $(docker images | awk "/^<none>/ {print \$3}")
}

set_minikube_env() {
  eval $(minikube docker-env)
}

clear_minikube_env() {
  unset DOCKER_HOST
  unset DOCKER_API_VERSION
  unset DOCKER_TLS_VERIFY
  unset DOCKER_CERT_PATH
}

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

set_minikube_env

kubectl delete job cpp-framework python-framework urb-executor-runner
kubectl delete deployment,service urb
delete_wait jobs urb-executor-runner
kubectl get pods -a
delete_wait pods urb-executor-runner

rmi "local\/urb-service"
rmi "local\/urb-cpp-framework"
rmi "local\/urb-python-framework"
rmi "local\/urb-executor-runner"
rmi_none

clear_minikube_env
pushd urb-core/vagrant
SYNCED_FOLDER=../.. vagrant ssh -- "cd /scratch/urb; rm -rf source/python/build source/python/dist urb-core/dist urb-core/source/python/dist urb-core/source/python/build && make && make dist"
popd

set_minikube_env
make images

kubectl create -f source/urb-master.yaml
kubectl get pods

