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

# create URB artifacts to be used in k8s persistent volume
prepare_urb_pv() {
  local root=/tmp/urb-k8s-volume/urb
  rm -rf $root
  mkdir -p $root/bin
  cp urb-core/dist/urb-*-linux-x86_64/bin/linux-x86_64/fetcher \
    urb-core/dist/urb-*-linux-x86_64/bin/linux-x86_64/command-executor \
    urb-core/dist/urb-*-linux-x86_64/bin/linux-x86_64/redis-cli \
    $root/bin
  mkdir -p $root/lib
  cp urb-core/dist/urb-*-linux-x86_64/lib/linux-x86_64/liburb* $root/lib
  cp -r urb-core/dist/urb-*/share $root
}

# create URB and Spark artifacts to be used in k8s persistent volume
prepare_spark_pv() {
  # Download and extract Spark
  if [ ! -d /tmp/spark-k8s-volume/spark-2.1.0-bin-hadoop2.7 ]; then
    mkdir -p /tmp/spark-k8s-volume
    wget -c d3kbcqa49mib13.cloudfront.net/spark-2.1.0-bin-hadoop2.7.tgz
    tar -C /tmp/spark-k8s-volume -xzf spark-2.1.0-bin-hadoop2.7.tgz
    cp /tmp/spark-k8s-volume/spark-2.1.0-bin-hadoop2.7/conf/spark-defaults.conf.template /tmp/spark-k8s-volume/spark-2.1.0-bin-hadoop2.7/conf/spark-defaults.conf
    # executor has to know SPARK_HOME
    echo "spark.mesos.executor.home /opt/spark-2.1.0-bin-hadoop2.7" >> /tmp/spark-k8s-volume/spark-2.1.0-bin-hadoop2.7/conf/spark-defaults.conf
  fi
}

# create data PV
prepare_scratch_pv() {
  local root=/tmp/scratch-k8s-volume
  rm -rf $root
  mkdir -p $root
  cp README.md $root
}

# clean k8s cluster
clean() {
  kubectl delete -f source/urb-master.yaml
  kubectl delete -f test/spark/spark.yaml
  kubectl delete jobs $(kubectl get jobs -a|awk '/urb-exec/ {print $1}')
  kubectl delete pods $(kubectl get pods -a|awk '/urb-exec/ {print $1}')
  kubectl delete -f test/spark/pvc.yaml
  kubectl delete -f test/spark/pv.yaml
  kubectl delete -f test/urb-pvc.yaml
  kubectl delete -f test/urb-pv.yaml
  kubectl delete -f test/spark/scratch-pvc.yaml
  kubectl delete -f test/spark/scratch-pv.yaml
}

# create URB persistent volume
create_urb_pv() {
  local mount_cmd="minikube mount --msize 1048576 /tmp/urb-k8s-volume/urb:/urb"
  pkill -f "$mount_cmd"
  $mount_cmd &
  mount_pid=$!

  kubectl create -f test/urb-pv.yaml
  kubectl create -f test/urb-pvc.yaml
}

# create persistent volume
create_spark_pv() {
  local mount_cmd="minikube mount --msize 1048576 /tmp/spark-k8s-volume/spark-2.1.0-bin-hadoop2.7:/spark-2.1.0-bin-hadoop2.7"
  pkill -f "$mount_cmd"
  $mount_cmd &
  mount_pid=$!

  kubectl create -f test/spark/pv.yaml
  kubectl create -f test/spark/pvc.yaml
}

# create persistent volume
create_scratch_pv() {
  local mount_cmd="minikube mount --msize 1048576 /tmp/scratch-k8s-volume:/scratch"
  pkill -f "$mount_cmd"
  $mount_cmd &
  mount_pid=$!

  kubectl create -f test/spark/scratch-pv.yaml
  kubectl create -f test/spark/scratch-pvc.yaml
}

configmap() {
  kubectl get configmap urb-config 2> /dev/null
  if [ $? -ne 0 ]; then
    kubectl create configmap urb-config --from-file=etc/urb.conf
  else
    kubectl create configmap urb-config --from-file=etc/urb.conf --dry-run -o yaml | kubectl replace -f -
  fi
}

cd test/spark
docker build --rm -t local/spark -f spark.dockerfile .
cd -
prepare_urb_pv
prepare_spark_pv
prepare_scratch_pv
clean
create_urb_pv
create_spark_pv
create_scratch_pv

configmap
kubectl create -f source/urb-master.yaml
kubectl create -f test/spark/spark.yaml

