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
#URB_K8S_GITHUB=github.com/UnivaCorporation/urb-k8s/blob/master
URB_K8S_GITHUB=https://raw.githubusercontent.com/sutasu/urb-k8s/master
#URB_K8S_GITHUB=https://raw.githubusercontent.com/UnivaCorporation/urb-k8s/master
DOCKER_HUB_REPO=univa
REPO=$DOCKER_HUB_REPO

CURL="curl -s"

Usage() {
   cat >&2 <<EOF
Univa Universal Resource Broker on Kubernetes installation script.

With no prameters only URB master is installed and URB will be configured to
use Univa Docker Hub repository (hub.docker.com/u/univa) directly.
--repo parameter can be provided to pull docker images from Univa
Docker Hub into docker repository used by your Kubernetes cluster.

Usage: $THISSCRIPT [options]

Options:
   --help|-h       : This output
   --repo|-r       : Docker repository used by Kubernetes cluster
                     URB images will be pulled to
                     (i.e --repo gcr.io/projectname ).
   --components|-c : Comma-separated components to install from
                     following list:
                       urb
                       urb-chronos
                       urb-marathon
                       urb-spark
                       urb-zoo (optional: installed automatically as
                         dependency)
   --remove        : Remove components specified with --components option
   --HA            : Install in highly available mode.
   --verbose       : Turn on verbose output
EOF
}

urb_configmap() {
  kubectl get configmap urb-config 2> /dev/null
  if [ $? -ne 0 ]; then
    kubectl create configmap urb-config --from-file=urb.conf
  else
    kubectl create configmap urb-config --from-file=urb.conf --dry-run -o yaml | kubectl replace -f -
  fi
}

get_uri() {
  local fr=$1
  local sp='/-\|'
  local n=${#sp}
  local max=60
  local cnt=0
  local ip=""
  local port=""
  EXTERNAL_URI=""
  echo "Waiting for external ip address to be available for ${fr}..."
  while [ $cnt -le $max ]; do
    ip=$(kubectl get service $ft | awk "/$fr/ {print \$3}")
    if [[ "$ip" == *"."*"."*"."* ]]; then
      port=$(kubectl get service $ft | awk "/$fr/ {print \$4}" | awk -F: "{print \$1}")
      EXTERNAL_URI="${ip}:${port}"
      return
    fi
    let cnt=cnt+1
    sleep 1
    printf "%s\r" "$cnt ${sp:cnt%n:1}"
  done
  if [ $cnt -ge $max ]; then
    echo "Timed out"
  fi
}

urb() {
  if [ -z "$REMOVE" ]; then
    $CURL $URB_K8S_GITHUB/etc/urb.conf.template | sed "s/K8SAdapter()/K8SAdapter('$REPO')/" > urb.conf
    urb_configmap
    $CURL $URB_K8S_GITHUB/source/urb-master.yaml | sed "s/image: local/image: $REPO/" | kubectl create -f -
  else
    kubectl delete service urb-master
    kubectl delete deployment urb-master
    kubectl delete configmap urb-config
    mv urb.conf urb.conf.removed
  fi
}

zookeeper() {
  if [ -z "$REMOVE" ]; then
    if [ -z "$ZOO_INSTALLED" ]; then
      if [ -z "$HA" ]; then
        $CURL $URB_K8S_GITHUB/test/marathon/kubernetes-zookeeper-master/zoo-rc.yaml | kubectl create -f -
        $CURL $URB_K8S_GITHUB/test/marathon/kubernetes-zookeeper-master/zoo-service.yaml | kubectl create -f -
      else
        echo "Zookeper HA not implemented"
        exit 1
      fi
      ZOO_INSTALLED=1
    fi
  else
    if [ -z "$ZOO_DELETED" ]; then
      if [ -z "$HA" ]; then
        $CURL $URB_K8S_GITHUB/test/marathon/kubernetes-zookeeper-master/zoo-service.yaml | kubectl delete -f -
        $CURL $URB_K8S_GITHUB/test/marathon/kubernetes-zookeeper-master/zoo-rc.yaml | kubectl delete -f -
      else
        echo "Zookeper HA not implemented"
        exit 1
      fi
    fi
    ZOO_DELETED=1
  fi
}

chronos() {
  if [ -z "$REMOVE" ]; then
    $CURL $URB_K8S_GITHUB/install/chronos/urb-chronos.yaml | sed "s/image: local/image: $REPO/;s/NodePort/LoadBalancer/" | kubectl create -f -
    kubectl create configmap urb-config --from-file=urb.conf --dry-run -o yaml | kubectl replace -f -
  else
    kubectl delete service urb-chronos
    kubectl delete deployment urb-chronos
    #$CURL $URB_K8S_GITHUB/install/chronos/urb-chronos.yaml | sed "s/image: local/image: $REPO/;s/NodePort/LoadBalancer/" | kubectl delete -f -
  fi
}

marathon() {
  if [ -z "$REMOVE" ]; then
    $CURL $URB_K8S_GITHUB/install/marathon/marathon.yaml | sed "s/image: local/image: $REPO/" | kubectl create -f -
    kubectl create configmap urb-config --from-file=urb.conf --dry-run -o yaml | kubectl replace -f -
  else
    kubectl delete service marathonsvc
    kubectl delete deployment marathonsvc
    #$CURL $URB_K8S_GITHUB/install/marathon/marathon.yaml | sed "s/image: local/image: $REPO/" | kubectl delete -f -
  fi
}

spark() {
  if [ -z "$REMOVE" ]; then
#    SPARK_PVC=$($CURL $URB_K8S_GITHUB/install/spark/spark-driver.yaml | awk -F":" "/claimName/ { print $2}")
#    echo "Spark expects persistent volume with persistent volume claim $SPARK_PVC"
#    echo "to be available in the cluster which will be mounted to /scratch"
#    echo "directory inside the driver and executor containers for user's data"
#    if ! kubectl get pvc | grep $SPARK_PVC ; then
#      echo "No persistent volume claim $SPARK_PVC found"
#      echo "Spark will not be installed"
#      #exit 1
#    fi
    $CURL $URB_K8S_GITHUB/install/spark/spark.conf | sed "s|local/urb-spark-exec|$REPO/urb-spark-exec|" >> urb.conf
    $CURL $URB_K8S_GITHUB/install/spark/spark-driver.yaml | sed "s/image: local/image: $REPO/" | kubectl create -f -
    kubectl create configmap urb-config --from-file=urb.conf --dry-run -o yaml | kubectl replace -f -
  else
    kubectl delete job spark-driver
    #$CURL $URB_K8S_GITHUB/install/spark/spark-driver.yaml | sed "s/image: local/image: $REPO/" | kubectl delete -f -
  fi
}



COMPONENTS=()
IMAGES=()
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
    urb=0
    co=$1
    oIFS=$IFS
    IFS=","
    for c in $co; do
      if [ "$c" == "urb-spark" ]; then
        IMAGES+=("spark-driver")
        IMAGES+=("spark-exec")
      else
        IMAGES+=($c)
      fi
      if [ "$c" == "urb" ]; then
        urb=1
      else
        COMPONENTS+=($c)
      fi
#      echo ${COMPONENTS[@]}
    done
    if [ $urb -eq 1 ]; then
      COMPONENTS=("urb" ${COMPONENTS[@]})
    fi
    if [[ "$co" == *"marathon"* ]] || [[ "$co" == *"chronos"* ]]; then
      ZOO=1
    fi
    IFS=$oIFS
    shift
    ;;
  "--remove")
    shift
    REMOVE=1
    ;;
  "--HA")
    shift
    HA=1
    ;;
  "--verbose")
    shift
    set -x
    ;;
  *)
    Usage
    echo "" >&2
    echo "Unknown command-line option $1" >&2
    exit 1
    ;;
  esac
done


if [ ${#COMPONENTS[@]} -eq 0 ]; then
  COMPONENTS=("urb")
  IMAGES=("urb-redis urb-service urb-executor-runner")
fi

if [ $REPO != "univa" ]; then
  for im in ${IMAGES[@]}; do
    docker pull univa/$im
    docker tag univa/$im $REPO/$im
    if [ $REPO != "local" ]; then
      docker push $REPO/$im
    fi
  done
fi


if [ ! -z "$ZOO" ] && [ -z "$REMOVE" ]; then
  zookeeper
fi

for comp in ${COMPONENTS[@]}; do
  case "$comp" in
  "urb")
    urb
    ;;
  "urb-chronos")
    chronos
    ;;
  "urb-marathon")
    marathon
    ;;
  "urb-spark")
    spark
    ;;
  "urb-zoo")
    # will not be installed second time
    zookeeper
    ;;
  *)
    echo "Invalid component: $comp" >&2
    ;;
  esac
done

if [ -z "$REMOVE" ]; then
  for comp in urb-chronos urb-marathon; do
    if [[ "${COMPONENTS[@]}" == *"$comp"* ]]; then
      get_uri $comp
      if [ ! -z "$EXTERNAL_URI" ]; then
        echo "$comp is available at: $EXTERNAL_URI"
      fi
    fi
  done
fi

# remove zookeeper at the end
if [ ! -z "$ZOO" ] && [ ! -z "$REMOVE" ] && [[ "${COMPONENTS[@]}" == *"urb-zoo"* ]]; then
  zookeeper
fi
