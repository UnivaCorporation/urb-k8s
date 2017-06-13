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

#export KUBECONFIG=/vagrant/.kube/config
#HOST_DIST_PATH=$(find urb-core/dist -maxdepth 1 -regex "urb-core/dist/urb-[1-9]+\.[0-9]+\.[0-9]$" -print)
#HOST_PROJECT_PATH=$(pwd | sed "s|$HOME/||")
# path to URB dist inside minikube
#MINIKUBE_DIST_PATH=/hosthome/$USER/$HOST_PROJECT_PATH/$HOST_DIST_PATH
#echo "MINIKUBE_DIST_PATH=$MINIKUBE_DIST_PATH"
#minikube mount /home/sutasu/Projects/URB/urb-k8s/urb-core/dist/urb-1.4.2:/urb&
#sed "s|path_template|$MINIKUBE_DIST_PATH|" system-test/pv.yaml | kubectl create -f -


# create URB artifacts to be used in k8s volume
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

exit
#HOST_DIST_PATH=$(find $(pwd)/urb-core/dist -maxdepth 1 -regex "$(pwd)/urb-core/dist/urb-[1-9]+\.[0-9]+\.[0-9]$" -print)
#minikube mount $HOST_DIST_PATH:/urb&
minikube mount /tmp/urb-k8s-volume:/urb&
mount_pid=$!
kubectl create -f system-test/pv.yaml
kubectl create -f system-test/pvc.yaml

kubectl create -f system-test/cpp-framework.yaml
kubectl create -f system-test/python-framework.yaml



#kill $mount_pid