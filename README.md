# Kubernetes adapter for Universal Resource Broker (URB)

This project allows one to run [Apache Mesos](http://mesos.apache.org) frameworks with Universal Resource Broker in [Kubernetes](https://kubernetes.io) cluster.

It utilizes [urb-core](https://github.com/UnivaCorporation/urb-core) project and provides Kubernetes adapter for URB.

Please see [Universal Resource Broker core](https://github.com/UnivaCorporation/urb-core) project for more architectual details.

Following steps need to be done to perform a project build:

## Install `kubectl` and `minikube` (requires `VirtualBox` to be installed)`:

`curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl && chmod a+x kubectl && sudo mv kubectl /usr/local/bin`
`curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 && chmod +x minikube && sudo mv minikube /usr/local/bin`

## Start `minikube`

`minikube start`

## Create kubernetes configuration to be used inside the build container

`./conf.sh`

## Create docker build environment (requires docker to be installed):

`cd urb-core/vagrant`

`make`

## Start docker build container:

`SYNCED_FOLDER=../.. vagrant up`

## Login into docker build container:

`vagrant ssh`

Inside the build container:

### Install `kubectl`:

`curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl && chmod a+x kubectl && sudo mv kubectl /usr/local/bin`

### Build

`cd /scratch/urb`

`make`

### Test

`export KUBECONFIG=/vagrant/.kube/config`

`kubectl proxy&`

`make test`

### Create distribution

`make dist`

## Open new shell, (in a root of the project) create docker images for URB service and example frameworks (reusing minikube's docker daemon):

`eval $(minikube docker-env)`

`make images`

## Run Mesos frameworks

URB service in minikube kubernetes cluster can be started with following command:

`kubectl create -f source/urb-master.yaml`

There are two options to run Mesos framework schedulers: within kubernetes cluster and outside of kubernetes cluster.

In both cases `LD_LIBRARY_PATH` and `MESOS_NATIVE_JAVA_LIBRARY` (for Java or Scala based frameworks) environment variables has to be specified for the run time environment of the framework. `LD_LIBRARY_PATH` has to contain a path to URB `liburb.so` shared library. `MESOS_NATIVE_JAVA_LIBRARY` should point to the same library file. Different frameworks may have different ways of specifing Mesos master URI. In general standard Mesos URI has to be changed to URB one: `urb://urb-master:6379` .

### Run Mesos framework inside kubernetes cluster

Framework has to be "dockerized" and associated with corresponding kubernetes object like pod, deployment, service, etc.
Following run time dependencied are required to be installed in docker container for the framework: `libev`, `libuuid`, `zlib` as well as `liburb.so` and `LD_LIBRARY_PATH` and/or `MESOS_NATIVE_JAVA_LIBRARY` set (see for example [C++ example framework](cpp-framework.dockerfile), [Python example framework](python-framework.dockerfile), [Marathon](test/marathon/marathon.dockerfile)) and URB URI specified as `urb://urb-master.default:6379` ([Marathon](test/marathon/marathon.yaml)).

In many situations, especially when framework uses custom executor or executor requires massive run time which is shared by framework scheduler and executor, it is convenient to have common run time located on persistent volume which is accessable from executor runner and framework. `urb-pvc` persistent volume claim name is predefined and mounted to `/opt` by URB executor runner making possible to place framework files to this location and share them within the cluster. For example 

### Run Mesos framework from outside of the kubernetes cluster

URB service can be accessable from outside of the cluster on port `30379`. In the development environment with minikube URB uri
can be retrieved with: `minikube service urb-master --format "urb://{{.IP}}:{{.Port}}"`. It is crucial to have framework runtime installed on the same paths inside and outside of kubernetes cluster as well as to have same URB related paths (`LD_LIBRARY_PATH`, `MESOS_NATIVE_JAVA_LIBRARY`) properly set. Since URB executor runner relies on `/opt` path, it can be used as a base for the frameworks installation.

## Run C++ and Python example frameworks

Directory [test/example-frameworks](test/example-frameworks)

On order to run C++ and Python example frameworks:

- URB service has to be running (`kubectl create -f source/urb-master.yaml`),
- persisten volume keeping custom executors has to be created in minikube,
- example frameworks started:

```
    kubectl create -f test/example-frameworks/cpp-framework.yaml
    kubectl create -f test/example-frameworks/python-framework.yaml
```
- an output from the frameworks can be examined with:

```
    kubectl logs cpp-framework-ck8zz
    kubectl python-framework-f537l
```

Following script [test/example-frameworks/run.sh](test/example-frameworks/run.sh) runs both frameworks in minikube environment.

## Run Marathon Mesos framework

