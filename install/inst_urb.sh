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
else
  URB_K8S_GITHUB=https://raw.githubusercontent.com/$GITHUB_USER/urb-k8s/master
  CURL="curl -s"
fi
REPO=$DOCKERHUB_USER
KUBECTL=kubectl
KUBECTL_CONFIG=kubectl
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
                       urb-singularity
                       urb-zeppelin
                       urb-zoo (optional: installed automatically as
                         dependency if required)
   --remove        : Remove components specified with --components option
   --namespace     : Kubernetes namespace (will be created if doesn't exist)
                     "default" is used by default
   --navops        : Install in Navops (see navops.io) environment
   --HA            : Install in highly available mode (not implemented)
   --dot-progress  : display dots instead of spinning progress
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

SPINNER='/-\|'
SPINNER_LEN=${#SPINNER}

progress() {
  local cnt=$1
  if [ -z $DOT_PROGRESS ]; then
    printf "%s\r" "$cnt ${SPINNER:cnt%SPINNER_LEN:1}"
  else
    echo -n "."
  fi
}

get_service_uri() {
  local fr=$1
  local max=${2:-120}
  local cnt=0
  local url=""
  EXTERNAL_URI=""
  echo "Waiting for public URL to become available for ${fr}..."
  while [ $cnt -le $max ]; do
    url=$($KUBECTL get service $fr -o=go-template='{{range .status.loadBalancer.ingress}}{{.ip}}:{{end}}{{range .spec.ports}}{{.port}}{{end}}')
    if [[ "$url" == *"."*"."*"."*":"* ]]; then
      EXTERNAL_URI="$url"
      return
    fi
    let cnt=cnt+1
    if [ $cnt -eq 11 ]; then
      echo "It may take a couple of minutes... You can ^C and use command \"$KUBECTL get service ${fr}\" later"
    fi
    sleep 1
    progress $cnt
  done
  if [ $cnt -ge $max ]; then
    echo "Timed out... You can try to obtain it later with \"$KUBECTL get service ${fr}\""
  fi
}

pod_wait() {
  local name=$1
  local max=${2:-120}
  local msg=${3:-}
  local cnt=0
  while ! $KUBECTL get pods | grep -q "$name.*Running" && [ $cnt -le $max ]; do
    let cnt=cnt+1
    sleep 1
    progress $cnt
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
  local timeout=${2:-180}
  context_name=$($KUBECTL config get-contexts | awk "/^\*/ {print \$2}")
  if [ "$context_name" == "minikube" ]; then
    if [ -z "$NAMESPACE" ]; then
      EXTERNAL_URI=$(minikube service $fr --url)
    else
      EXTERNAL_URI=$(minikube service --namespace=$NAMESPACE $fr --url)
    fi
  elif [ "$context_name" == "gke"* ]; then
    get_service_uri $fr $timeout
  else
    get_service_uri $fr $timeout
  fi
}

add_config() {
  local conf=$1
  local max=60
  local cnt=0
#  section=$($CURL $conf | tee -a $URB_CONF | grep FrameworkConfig | head -1)
  section=$(cat | tee -a $URB_CONF | grep FrameworkConfig | head -1)
  if [ -z "$section" ]; then
    echo "ERROR: Empty section"
  else
    urb_configmap
    URB_MASTER_POD=$($KUBECTL get pods | awk "/^urb-master/ {print \$1}")
    pod_wait $URB_MASTER_POD
#    while ! $KUBECTL exec $URB_MASTER_POD -c urb-service -- grep -q "$section" /urb/etc/urb.conf && [ $cnt -le $max ]; do
    while ! $KUBECTL exec $URB_MASTER_POD -c urb-service -- cat /urb/etc/urb.conf | grep -q "$section" && [ $cnt -le $max ]; do
#    while ! $KUBECTL describe configmap urb-config | grep -q "$section" && [ $cnt -le $max ]; do
      if [ $cnt -eq 0 ]; then
        echo "Waiting for URB configuration update for $section"
      fi
      let cnt=cnt+1
      sleep 1
      progress $cnt
    done
    if [ $cnt -ge $max ]; then
      echo "WARNING: Timeout waiting for URB configuration update for $section"
    fi
  fi
}

add_to_yaml() {
  local key=$1
  local val=$2
  local doc_num=$3
  cat | python /tmp/inst_urb_del.py "$key" "$val" $doc_num
}

navops() {
  local doc_num=${1:-0}
  local scheduler_key="spec:template:metadata:annotations:scheduler.alpha.kubernetes.io/name"
  local scheduler_val="navops-command"
  if [ -z "$NAVOPS" ]; then
    cat
  else
    if [ ! -z "$NAMESPACE" ]; then
      cat | add_to_yaml "metadata:namespace" "$NAMESPACE" $doc_num | add_to_yaml $scheduler_key $scheduler_val $doc_num
    else
      cat | add_to_yaml $scheduler_key $scheduler_val $doc_num
    fi
  fi
}

create_tmp_script() {
  cat > /tmp/inst_urb_del.py <<EOF
import sys
import yaml
docs = list(yaml.load_all(sys.stdin.read()))
d = docs[int(sys.argv[3]) if len(sys.argv) == 4 else 0]
l = sys.argv[1].split(":")
for key in l[:-1]:
    if not d.get(key):
        d[key] = {}
    d = d[key]
d[l[-1]] = sys.argv[2]
print yaml.dump_all(docs, explicit_start=True)
EOF
}

urb() {
  if [ -z "$REMOVE" ]; then
    if [ -f $URB_CONF ]; then
      echo "WARNING: local $URB_CONF file (possibly with customizations) already exists. Will not overwrite..."
    else
      $CURL $URB_K8S_GITHUB/etc/urb.conf.template | sed "s/K8SAdapter()/K8SAdapter('$REPO')/" > $URB_CONF
      urb_configmap
    fi
    # ClusterRoleBinding requires direct namespace substitution (no way to reference it from metadata for now)
    local ns=${NAMESPACE:-default}
    $CURL $URB_K8S_GITHUB/source/urb-master.yaml | sed "s/image: local/image: $REPO/;s/- key: urb.conf/- key: $URB_CONF/;s/namespace: default/namespace: $ns/" | navops 1 | $KUBECTL create -f -
#    $CURL $URB_K8S_GITHUB/source/urb-master.yaml | sed "s/image: local/image: $REPO/;s/- key: urb.conf/- key: $URB_CONF/;s/type: NodePort/type: LoadBalancer/" | navops 1 | $KUBECTL create -f -
  else
    $KUBECTL delete service urb-master
    $KUBECTL delete deployment urb-master
    $KUBECTL delete configmap urb-config
    $KUBECTL delete clusterrolebinding urb-master
    $KUBECTL delete serviceaccount urb-master
    if [ -f $URB_CONF ]; then
      mv $URB_CONF ${URB_CONF}.removed
    fi
  fi
}

zookeeper() {
  if [ -z "$REMOVE" ]; then
    if [ -z "$ZOO_INSTALLED" ]; then
      if [ -z "$HA" ]; then
        $CURL $URB_K8S_GITHUB/test/marathon/kubernetes-zookeeper-master/zoo-rc.yaml | navops | $KUBECTL create -f -
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
        $CURL $URB_K8S_GITHUB/test/marathon/kubernetes-zookeeper-master/zoo-rc.yaml | navops | $KUBECTL delete -f -
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
      echo
      urb_configmap
    else
      $CURL $URB_K8S_GITHUB/install/chronos/urb-chronos.conf | add_config
#      add_config $URB_K8S_GITHUB/install/chronos/urb-chronos.conf
    fi
    $CURL $URB_K8S_GITHUB/install/chronos/urb-chronos.yaml | sed "s/image: local/image: $REPO/;s/NodePort/LoadBalancer/" | navops 1 | $KUBECTL create -f -
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
      echo
      urb_configmap
    else
      $CURL $URB_K8S_GITHUB/install/marathon/urb-marathon.conf | add_config
#      add_config $URB_K8S_GITHUB/install/marathon/urb-marathon.conf
    fi
    $CURL $URB_K8S_GITHUB/install/marathon/urb-marathon.yaml | sed "s/image: local/image: $REPO/" | navops 1 | $KUBECTL create -f -
  else
    $KUBECTL delete service marathonsvc
    $KUBECTL delete deployment marathonsvc
    #$CURL $URB_K8S_GITHUB/install/marathon/marathon.yaml | sed "s/image: local/image: $REPO/" | $KUBECTL delete -f -
  fi
}

singularity() {
  if [ -z "$REMOVE" ]; then
    if grep -i 'Singularity.*FrameworkConfig]' $URB_CONF ; then
      echo "WARNING: Some Singularity related framework configuration section[s] outlined above already present in $URB_CONF"
      echo "The default one below will not be added:"
      $CURL $URB_K8S_GITHUB/install/singularity/urb-singularity.conf
      echo
      urb_configmap
    else
      $CURL $URB_K8S_GITHUB/install/singularity/urb-singularity.conf | add_config
    fi
    $CURL $URB_K8S_GITHUB/install/singularity/urb-singularity.yaml | sed "s/image: local/image: $REPO/" | navops 1 | $KUBECTL create -f -
  else
    $KUBECTL delete service urb-singularity
    $KUBECTL delete deployment urb-singularity
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
      echo
      urb_configmap
    else
      $CURL $URB_K8S_GITHUB/install/spark/spark.conf | sed "s|local/urb-spark-exec|$REPO/urb-spark-exec|" | add_config
#      $CURL $URB_K8S_GITHUB/install/spark/spark.conf | sed "s|local/urb-spark-exec|$REPO/urb-spark-exec|" >> $URB_CONF
    fi
    $CURL $URB_K8S_GITHUB/install/spark/urb-spark-driver.yaml | sed "s/image: local/image: $REPO/" | navops | $KUBECTL create -f -
  else
    $KUBECTL delete job spark-driver
    #$CURL $URB_K8S_GITHUB/install/spark/spark-driver.yaml | sed "s/image: local/image: $REPO/" | $KUBECTL delete -f -
  fi
}

zeppelin() {
  if [ -z "$REMOVE" ]; then
    if grep -i 'ZeppelinFrameworkConfig]' $URB_CONF ; then
      echo "WARNING: Some Zeppelin related framework configuration section[s] outlined above already present in $URB_CONF"
      echo "The default one below will not be added:"
      $CURL $URB_K8S_GITHUB/install/zeppelin/zeppelin.conf
      echo
      urb_configmap
    else
      $CURL $URB_K8S_GITHUB/install/zeppelin/zeppelin.conf | sed "s|local/urb-spark-exec|$REPO/urb-spark-exec|" | add_config
#      $CURL $URB_K8S_GITHUB/install/zeppelin/zeppelin.conf | sed "s|local/urb-spark-exec|$REPO/urb-spark-exec|" >> $URB_CONF
    fi
    $CURL $URB_K8S_GITHUB/install/zeppelin/zeppelin-rc.yaml | sed "s/image: local/image: $REPO/" | navops | $KUBECTL create -f -
    # service fails to start if we dont wait here
    echo "Waiting for Zeppelin to start"
    pod_wait zeppelin-rc 360 "Zeppelin is huge, it may take a long time to pull an image for the first time..."
    sleep 2
    $CURL $URB_K8S_GITHUB/install/zeppelin/zeppelin-service.yaml | $KUBECTL create -f -
  else
    $KUBECTL delete service urb-zeppelin
    $KUBECTL delete rc urb-zeppelin-rc
  fi
}

add_image() {
  local im=$1
  if [[ "${IMAGES[@]}" != *"$im"* ]]; then
    IMAGES+=($im)
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
        add_image "urb-spark-driver"
        add_image "urb-spark-exec"
      elif [ "$c" == "urb-zeppelin" ]; then
        add_image "urb-spark-exec"
        add_image "$c"
      else
        add_image "$c"
      fi
      if [ "$c" == "urb" ]; then
        URB_IN_COMPONENTS=1
      else
        COMPONENTS+=($c)
      fi
#      echo ${COMPONENTS[@]}
    done
    if [[ "$co" == *"marathon"* ]] || [[ "$co" == *"chronos"* ]] || [[ "$co" == *"singularity"* ]]; then
      ZOO=1
    fi
    IFS=$oIFS
    shift
    ;;
  "--namespace")
    shift
    NAMESPACE=$1
    shift
#    KUBECTL+=" --namespace=$NAMESPACE"
    URB_CONF+=".$NAMESPACE"
    ;;
  "--navops")
    shift
    KUBECTL_CONFIG=navopsctl
    NAVOPS=1
    ;;
  "--remove")
    shift
    REMOVE=1
    ;;
  "--HA")
    shift
    HA=1
    ;;
  "--dot-progress")
    shift
    DOT_PROGRESS=1
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


NAVOPS_NS_YAML="metadata: { apiVersion: v1, type: Namespace, uid: $NAMESPACE }"

# regular k8s environment
if [ -z "$NAVOPS" ]; then
  if [ ! -z "$NAMESPACE" ]; then
    KUBECTL+=" --namespace=$NAMESPACE"
    KUBECTL_CONFIG+=" --namespace=$NAMESPACE"
  fi
  if [ -z "$REMOVE" ] && [ ! -z "$NAMESPACE" ] && ! kubectl get namespaces | grep "^urb[ \t]" > /dev/null 2>&1 ; then
    kubectl create namespace $NAMESPACE
    kubectl label namespace $NAMESPACE name=urb
  fi
else # Navops environment
  if [ ! -z "$NAMESPACE" ]; then
    KUBECTL_CONFIG+=" --namespace=$NAMESPACE"
    if ! echo $NAVOPS_NS_YAML | navopsctl update -f - > /dev/null 2>&1 ; then
      echo $NAVOPS_NS_YAML | navopsctl create -f -
    fi
  fi
fi

create_tmp_script


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
  "urb-singularity")
    singularity
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
  if [[ "${COMPONENTS[@]}" == *"spark"* ]]; then
    pod_wait spark-driver 60
    spark_driver=$($KUBECTL get pod | awk '/spark-driver.*Running/ {print $1}')
    echo "Spark driver pod $spark_driver can be used to run Spark command line tools, for example:"
    echo "kubectl exec $spark_driver -it -- /opt/spark-2.1.0-bin-hadoop2.7/bin/spark-submit --name SparkPi --master mesos://urb://urb-master:6379 /opt/spark-2.1.0-bin-hadoop2.7/examples/src/main/python/pi.py"
  fi
  for comp in urb-chronos urb-marathon urb-singularity urb-zeppelin; do
    if [[ "${COMPONENTS[@]}" == *"$comp"* ]]; then
      if [ "$comp" == "urb-marathon" ]; then
        get_uri marathonsvc
      else
        get_uri $comp
      fi
      if [ ! -z "$EXTERNAL_URI" ]; then
        if [ "$comp" == "urb-singularity" ]; then
          echo "$comp is available at: $EXTERNAL_URI/singularity"
        else
          echo "$comp is available at: $EXTERNAL_URI"
        fi
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
  echo "$KUBECTL create configmap urb-config --from-file=$URB_CONF --dry-run -o yaml | $KUBECTL replace -f -"
fi
