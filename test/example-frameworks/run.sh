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

# wait for framework run completion
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
  mkdir -p /tmp/urb-k8s-volume/urb/bin
  cp urb-core/dist/urb-*-linux-x86_64/bin/linux-x86_64/fetcher \
    urb-core/dist/urb-*-linux-x86_64/bin/linux-x86_64/command-executor \
    urb-core/dist/urb-*-linux-x86_64/bin/linux-x86_64/redis-cli \
    /tmp/urb-k8s-volume/urb/bin
  mkdir -p /tmp/urb-k8s-volume/urb/lib
  cp urb-core/dist/urb-*-linux-x86_64/lib/linux-x86_64/liburb* /tmp/urb-k8s-volume/urb/lib
  cp -r urb-core/dist/urb-*/share /tmp/urb-k8s-volume/urb

  mkdir -p /tmp/urb-k8s-volume/bin
  # add cpp test framework
  cp urb-core/dist/urb-*-linux-x86_64/share/examples/frameworks/linux-x86_64/example_*.test /tmp/urb-k8s-volume/bin
  # add python test framework
  cp urb-core/dist/urb-*/share/examples/frameworks/python/*.py /tmp/urb-k8s-volume/bin
}

# clean k8s cluster
clean() {
  kubectl delete -f source/urb-master.yaml
  kubectl delete -f test/example-frameworks/cpp-framework.yaml
  kubectl delete -f test/example-frameworks/python-framework.yaml
  kubectl delete jobs $(kubectl get jobs -a|awk '/urb-exec/ {print $1}')
  kubectl delete pods $(kubectl get pods -a|awk '/urb-exec/ {print $1}')
  kubectl delete -f test/example-frameworks/pvc.yaml
  kubectl delete -f test/example-frameworks/pv.yaml
}

# create persistent volume
create_pv() {
  pkill -f "minikube mount"
  minikube mount /tmp/urb-k8s-volume:/urb&
  mount_pid=$!

  kubectl create -f test/example-frameworks/pv.yaml
  kubectl create -f test/example-frameworks/pvc.yaml
}

prepare_pv
clean
create_pv

kubectl create -f source/urb-master.yaml
sleep 3
kubectl create -f test/example-frameworks/cpp-framework.yaml
kubectl create -f test/example-frameworks/python-framework.yaml

framework_wait python-framework "exiting with status 0" 60
framework_wait cpp-framework "example_framework: ~TestScheduler()" 60

#if [ ! -z "$mount_pid" ]; then
#  kill $mount_pid
#fi

exit $RET
