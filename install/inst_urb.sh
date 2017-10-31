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
GITHUB_USER=${GITHUB_USER:-UnivaCorporation}
DOCKERHUB_USER=${DOCKERHUB_USER:-univa}
# with LOCAL_TEST take yaml files from local project and docker images from "local" repository
if [ ! -z "$LOCAL_TEST" ]; then
  URB_K8S_GITHUB=./
  CURL="cat"
  REPO=local
  DOCKERHUB_USER=local
else
  URB_K8S_GITHUB=https://raw.githubusercontent.com/$GITHUB_USER/urb-k8s/master
  CURL="curl -s"
  REPO=$DOCKERHUB_USER
fi
KUBECTL=kubectl
URB_CONF=urb.conf

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
                     (i.e --repo gcr.io/projectname)
   --components|-c : Comma-separated components to install from
                     following list:
                       urb
                       urb-chronos
                       urb-marathon
                       urb-spark
                       urb-zeppelin
                       urb-zoo (optional: installed automatically as
                         dependency if required)
   --remove        : Remove components specified with --components option
   --namespace     : Kubernetes namespace (will be created if doesn't exist)
                     "default" is used by default
   --HA            : Install in highly available mode (not implemented)
   --verbose       : Turn on verbose output
EOF
}

urb_configmap() {
  $KUBECTL get configmap urb-config > /dev/null 2>&1
  if [ $? -ne 0 ]; then
    $KUBECTL create configmap urb-config --from-file=$URB_CONF
  else
    $KUBECTL create configmap urb-config --from-file=$URB_CONF --dry-run -o yaml | $KUBECTL replace -f -
  fi
}

get_service_uri() {
  local fr=$1
  local sp='/-\|'
  local n=${#sp}
  local max=120
  local cnt=0
  local ip=""
  local port=""
  EXTERNAL_URI=""
  echo "Waiting for external ip address to become available for ${fr}..."
  while [ $cnt -le $max ]; do
    ip=$($KUBECTL get service $fr | awk "/$fr/ {print \$3}")
    if [[ "$ip" == *"."*"."*"."* ]]; then
      port=$($KUBECTL get service $fr | awk "/$fr/ {print \$4}" | awk -F: "{print \$1}")
      EXTERNAL_URI="${ip}:${port}"
      return
    fi
    let cnt=cnt+1
    if [ $cnt -eq 6 ]; then
      echo "It may take a couple of minutes... You can ^C and get it later with \"$KUBECTL get service ${fr}\""
    fi
    sleep 1
    printf "%s\r" "$cnt ${sp:cnt%n:1}"
  done
  if [ $cnt -ge $max ]; then
    echo "Timed out... You can try to obtain it later with \"$KUBECTL get service ${fr}\""
  fi
}

pod_wait() {
  local name=$1
  local max=${2:-60}
  local msg=${3:-}
  local cnt=0
  local sp='/-\|'
  local n=${#sp}
  while ! kubectl get pods | grep "$name.*Running" && [ $cnt -le $max ]; do
    let cnt=cnt+1
    sleep 1
    printf "%s\r" "$cnt ${sp:cnt%n:1}"
    if [ ! -z "$msg" ] && [ $cnt -eq 6 ]; then
      echo "${msg}"
    fi
  done
  if [ $cnt -ge $max ]; then
    echo "WARNING: Timeout waiting for $name pod to start"
  fi
}

get_uri() {
  local fr=$1
  context_name=$($KUBECTL config get-contexts | awk "/^\*/ {print \$2}")
  if [ "$context_name" == "minikube" ]; then
    EXTERNAL_URI=$(minikube service $fr --url)
  elif [ "$context_name" == "gke"* ]; then
    get_service_uri $fr
  else
    get_service_uri $fr
  fi
}

urb() {
  if [ -z "$REMOVE" ]; then
    if [ -f $URB_CONF ]; then
      echo "WARNING: local $URB_CONF file (possibly with customizations) already exists. Will not overwrite..."
    else
      $CURL $URB_K8S_GITHUB/etc/urb.conf.template | sed "s/K8SAdapter()/K8SAdapter('$REPO')/" > $URB_CONF
      urb_configmap
    fi
    $CURL $URB_K8S_GITHUB/source/urb-master.yaml | sed "s/image: local/image: $REPO/;s/- key: urb.conf/- key: $URB_CONF/" | $KUBECTL create -f -
  else
    $KUBECTL delete service urb-master
    $KUBECTL delete deployment urb-master
    $KUBECTL delete configmap urb-config
    if [ -f $URB_CONF ]; then
      mv $URB_CONF ${URB_CONF}.removed
    fi
  fi
}

zookeeper() {
  if [ -z "$REMOVE" ]; then
    if [ -z "$ZOO_INSTALLED" ]; then
      if [ -z "$HA" ]; then
        $CURL $URB_K8S_GITHUB/test/marathon/kubernetes-zookeeper-master/zoo-rc.yaml | $KUBECTL create -f -
        $CURL $URB_K8S_GITHUB/test/marathon/kubernetes-zookeeper-master/zoo-service.yaml | $KUBECTL create -f -
      else
        echo "Zookeper HA not implemented"
        exit 1
      fi
      ZOO_INSTALLED=1
    fi
  else
    if [ -z "$ZOO_DELETED" ]; then
      if [ -z "$HA" ]; then
        $CURL $URB_K8S_GITHUB/test/marathon/kubernetes-zookeeper-master/zoo-service.yaml | $KUBECTL delete -f -
        $CURL $URB_K8S_GITHUB/test/marathon/kubernetes-zookeeper-master/zoo-rc.yaml | $KUBECTL delete -f -
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
    if grep -i 'chronos.*FrameworkConfig]' $URB_CONF ; then
      echo "WARNING: Some Chronos related framework configuration section[s] outlined above already present in $URB_CONF"
      echo "The default one below will not be added:"
      $CURL $URB_K8S_GITHUB/install/chronos/urb-chronos.conf
    else
      $CURL $URB_K8S_GITHUB/install/chronos/urb-chronos.conf >> $URB_CONF
    fi
    urb_configmap
    $CURL $URB_K8S_GITHUB/install/chronos/urb-chronos.yaml | sed "s/image: local/image: $REPO/;s/NodePort/LoadBalancer/" | $KUBECTL create -f -
  else
    $KUBECTL delete service urb-chronos
    $KUBECTL delete deployment urb-chronos
    #$CURL $URB_K8S_GITHUB/install/chronos/urb-chronos.yaml | sed "s/image: local/image: $REPO/;s/NodePort/LoadBalancer/" | $KUBECTL delete -f -
  fi
}

marathon() {
  if [ -z "$REMOVE" ]; then
    if grep -i 'marathon.*FrameworkConfig]' $URB_CONF ; then
      echo "WARNING: Some Marathon related framework configuration section[s] outlined above already present in $URB_CONF"
      echo "The default one below will not be added:"
      $CURL $URB_K8S_GITHUB/install/marathon/urb-marathon.conf
    else
      $CURL $URB_K8S_GITHUB/install/marathon/urb-marathon.conf >> $URB_CONF
    fi
    urb_configmap
    $CURL $URB_K8S_GITHUB/install/marathon/urb-marathon.yaml | sed "s/image: local/image: $REPO/" | $KUBECTL create -f -
  else
    $KUBECTL delete service marathonsvc
    $KUBECTL delete deployment marathonsvc
    #$CURL $URB_K8S_GITHUB/install/marathon/marathon.yaml | sed "s/image: local/image: $REPO/" | $KUBECTL delete -f -
  fi
}

spark() {
  if [ -z "$REMOVE" ]; then
#    SPARK_PVC=$($CURL $URB_K8S_GITHUB/install/spark/spark-driver.yaml | awk -F":" "/claimName/ { print $2}")
#    echo "Spark expects persistent volume with persistent volume claim $SPARK_PVC"
#    echo "to be available in the cluster which will be mounted to /scratch"
#    echo "directory inside the driver and executor containers for user's data"
#    if ! $KUBECTL get pvc | grep $SPARK_PVC ; then
#      echo "No persistent volume claim $SPARK_PVC found"
#      echo "Spark will not be installed"
#      #exit 1
#    fi
    if grep -i 'spark.*FrameworkConfig]' $URB_CONF ; then
      echo "WARNING: Some Spark related framework configuration section[s] outlined above already present in $URB_CONF"
      echo "The default ones below will not be added:"
      $CURL $URB_K8S_GITHUB/install/spark/spark.conf
    else
      $CURL $URB_K8S_GITHUB/install/spark/spark.conf | sed "s|local/urb-spark-exec|$REPO/urb-spark-exec|" >> $URB_CONF
    fi
    urb_configmap
    $CURL $URB_K8S_GITHUB/install/spark/spark-driver.yaml | sed "s/image: local/image: $REPO/" | $KUBECTL create -f -
  else
    $KUBECTL delete job spark-driver
    #$CURL $URB_K8S_GITHUB/install/spark/spark-driver.yaml | sed "s/image: local/image: $REPO/" | $KUBECTL delete -f -
  fi
}

zeppelin() {
  if [ -z "$REMOVE" ]; then
    if grep -i 'ZeppelinFrameworkConfig]' $URB_CONF ; then
      echo "WARNING: Some Zeppelin related framework configuration section[s] outlined above already present in $URB_CONF"
      echo "The default ones below will not be added:"
      $CURL $URB_K8S_GITHUB/install/zeppelin/zeppelin.conf
    else
      $CURL $URB_K8S_GITHUB/install/zeppelin/zeppelin.conf | sed "s|local/urb-spark-exec|$REPO/urb-spark-exec|" >> $URB_CONF
    fi
    urb_configmap
    $CURL $URB_K8S_GITHUB/install/zeppelin/zeppelin-rc.yaml | sed "s/image: local/image: $REPO/" | $KUBECTL create -f -
    # have to wait
    echo "Waiting for Zeppelin to start"
    pod_wait zeppelin-rc 60 "Zeppelin is huge, it may take a long time to pull an image for the first time"
    $CURL $URB_K8S_GITHUB/install/zeppelin/zeppelin-service.yaml | $KUBECTL create -f -
  else
    $KUBECTL delete service zeppelin
    $KUBECTL delete rc zeppelin-rc
  fi
}



URB_IN_COMPONENTS=0
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
        URB_IN_COMPONENTS=1
      else
        COMPONENTS+=($c)
      fi
#      echo ${COMPONENTS[@]}
    done
    if [[ "$co" == *"marathon"* ]] || [[ "$co" == *"chronos"* ]]; then
      ZOO=1
    fi
    IFS=$oIFS
    shift
    ;;
  "--namespace")
    shift
    NAMESPACE=$1
    shift
    KUBECTL+=" --namespace=$NAMESPACE"
    URB_CONF+=".$NAMESPACE"
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


if ! kubectl get namespaces | grep "^urb[ \t]" > /dev/null 2>&1 ; then
  kubectl create namespace $NAMESPACE
  kubectl label namespace $NAMESPACE name=urb
fi

if [ ${#COMPONENTS[@]} -eq 0 ]; then
  COMPONENTS=("urb")
  IMAGES=("urb-redis urb-service urb-executor-runner")
else
  if [ $URB_IN_COMPONENTS -eq 1 ]; then
    if [ -z "$REMOVE" ]; then
      COMPONENTS=("urb" ${COMPONENTS[@]})
    else
      COMPONENTS=(${COMPONENTS[@]} "urb")
    fi
  fi
fi

if [ "$REPO" != "$DOCKERHUB_USER" ]; then
  for im in ${IMAGES[@]}; do
    docker pull $DOCKERHUB_USER/$im
    docker tag $DOCKERHUB_USER/$im $REPO/$im
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
  "urb-zeppelin")
    zeppelin
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
      if [ "$comp" == "urb-marathon" ]; then
        get_uri marathonsvc
      else
        get_uri $comp
      fi
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

if [ -z "$REMOVE" ]; then
  echo "URB configuration file $URB_CONF can be modified and reloaded with:"
  echo "$KUBECTL create configmap urb-config --from-file=$URB_CONF --dry-run -o yaml | kubectl replace -f -"
fi
