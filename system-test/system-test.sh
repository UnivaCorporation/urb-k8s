#/bin/bash

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
RET=0

#export KUBECONFIG=/vagrant/.kube/config
#HOST_DIST_PATH=$(find urb-core/dist -maxdepth 1 -regex "urb-core/dist/urb-[1-9]+\.[0-9]+\.[0-9]$" -print)
#HOST_PROJECT_PATH=$(pwd | sed "s|$HOME/||")
# path to URB dist inside minikube
#MINIKUBE_DIST_PATH=/hosthome/$USER/$HOST_PROJECT_PATH/$HOST_DIST_PATH
#echo "MINIKUBE_DIST_PATH=$MINIKUBE_DIST_PATH"
#minikube mount /home/sutasu/Projects/URB/urb-k8s/urb-core/dist/urb-1.4.2:/urb&
#sed "s|path_template|$MINIKUBE_DIST_PATH|" system-test/pv.yaml | kubectl create -f -

framework_wait() {
  local fr=$1
  local pattern=$2
  local sec=$3
  local sl=2
  local max=$((sec/sl))
  local cnt=0
  local pod=$(kubectl get pods | awk "/$fr.*Running/ || /$fr.*Container/ || /$fr.*Pending/ {print \$1}")
  if [ -z "$pod" ]; then
    echo "Cannot get pod name for framework $fr"
    RET=1
    exit 1
  fi
  sleep 5
  echo "Starting to wait for framework $fr on pod $pod for $sec sec"
  while ! kubectl logs $pod | tail -1 | grep "$pattern" && [ $cnt -le $max ]; do
    let cnt=cnt+1
    sleep $sl
  done
  if [ $cnt -ge $max ]; then
    echo "ERROR: Timeout waiting for framework $fr completion"
    RET=1
  fi
}

# create URB and frameworks artifacts to be used in k8s persistent volume
prepare_pv() {
  rm -rf /tmp/urb-k8s-volume
  # get URB version path
  URB_VER=$(basename $(find urb-core/dist -maxdepth 1 -regex "urb-core/dist/urb-[1-9]+\.[0-9]+\.[0-9]$" -print))
  mkdir -p /tmp/urb-k8s-volume/$URB_VER
  mkdir -p /tmp/urb-k8s-volume/$URB_VER/bin
  cp urb-core/dist/${URB_VER}-linux-x86_64/bin/linux-x86_64/fetcher \
    urb-core/dist/${URB_VER}-linux-x86_64/bin/linux-x86_64/command-executor \
    urb-core/dist/${URB_VER}-linux-x86_64/bin/linux-x86_64/redis-cli \
    /tmp/urb-k8s-volume/$URB_VER/bin
  mkdir -p /tmp/urb-k8s-volume/$URB_VER/lib
  cp urb-core/dist/${URB_VER}-linux-x86_64/lib/linux-x86_64/liburb.* /tmp/urb-k8s-volume/$URB_VER/lib
  cp -r urb-core/dist/$URB_VER/share /tmp/urb-k8s-volume/$URB_VER

  mkdir -p /tmp/urb-k8s-volume/bin
  # add cpp test framework
  cp urb-core/dist/urb-*-linux-x86_64/share/examples/frameworks/linux-x86_64/example_*.test /tmp/urb-k8s-volume/bin
  # add python test framework
  cp urb-core/dist/urb-*/share/examples/frameworks/python/*.py /tmp/urb-k8s-volume/bin
}

clean() {
  kubectl delete -f source/urb-master.yaml
  kubectl delete -f system-test/cpp-framework.yaml
  kubectl delete -f system-test/python-framework.yaml
  kubectl delete jobs $(kubectl get jobs -a|awk '/urb-executor-runner/ {print $1}')
  kubectl delete pods $(kubectl get pods -a|awk '/urb-executor-runner/ {print $1}')
  kubectl delete -f system-test/pvc.yaml
  kubectl delete -f system-test/pv.yaml
}

create_pv() {
  pkill -f "minikube mount"
  minikube mount /tmp/urb-k8s-volume:/urb&
  mount_pid=$!

  kubectl create -f system-test/pv.yaml
  kubectl create -f system-test/pvc.yaml
}

prepare_pv
clean
create_pv

kubectl create -f source/urb-master.yaml
sleep 3
kubectl create -f system-test/cpp-framework.yaml
kubectl create -f system-test/python-framework.yaml

framework_wait python-framework "exiting with status 0" 60
framework_wait cpp-framework "example_framework: ~TestScheduler()" 60

#if [ ! -z "$mount_pid" ]; then
#  kill $mount_pid
#fi

exit $RET
