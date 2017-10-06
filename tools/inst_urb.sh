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

THISSCRIPT=$(basename $0)
URB_K8S_GITHUB=github.com/UnivaCorporation/urb-k8s
DOCKER_HUB_REPO=univa
REPO=$DOCKER_HUB_REPO

Usage() {
   cat >&2 <<EOF
Univa Universal Resource Broker on Kubernetes installation script.

With no prameters only URB master is installed. URB will be configured to
use Univa Docker Hub repository (hub.docker.com/u/univa).
It is recommended to provide --repo parameter to pull docker images from
Docker Hub into local docker repository used by Kubernetes.

Usage: $THISSCRIPT [options]

Options:
   --help|-h       : This output
   --repo|-r       : Local docker repository accessible from Kubernetes cluster.
   --components|-c : Comma-separated additional components to install from list:
                       urb-chronos
                       urb-marathon
                       urb-spark
   --verbose       : Turn on verbose output
EOF
}

configmap() {
  kubectl get configmap urb-config 2> /dev/null
  if [ $? -ne 0 ]; then
    kubectl create configmap urb-config --from-file=urb.conf
  else
    kubectl create configmap urb-config --from-file=urb.conf --dry-run -o yaml | kubectl replace -f -
  fi
}


# Command-line parsing
while [ $# -gt 0 ]; do
  case "$1" in
  "--help" | "-h")
    Usage
    exit 0
    ;;
  "--repo" | "-r")
    shift
    REPO="$1"
    shift
    ;;
  "--components" | "-c")
    shift
    oIFS=$IFS
    IFS=","
    for c in "$1"; do
      COMPONENTS="$COMPONENTS $c"
    done
    IFS=$oIFS
    shift
    ;;
  *)
    Usage
    echo "" >&2
    Fail "Unknown command-line option $1"
    ;;
  esac
done

if [ $REPO != "univa" ]; then
  for im in univa/urb-redis univa/urb-service univa/urb-executor-runner $(for i in $COMPONENTS; do echo "univa/$i"; done); do
    docker pull $im
  done
fi

curl $URB_K8S_GITHUB/etc/urb.conf.template | sed "s/K8SAdapter()/K8SAdapter('$REPO')/" > urb.conf
configmap

curl $URB_K8S_GITHUB/source/urb-master.yaml | sed "s/image: local/image: $REPO/" | kubectl create -f -

for comp in $COMPONENTS; do
  case "$comp" in
  "urb-chronos")
    curl URB_K8S_GITHUB/test/chronos/urb-chronos.yaml | sed "s/image: local/image: $REPO/" | kubectl create -f -
    ;;
  *)
    echo "Bad component: $comp" >&2
    ;;
  esac
done

