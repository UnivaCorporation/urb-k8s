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

## Open new shell, (in a root of the project) create docker images for URB services (reusing minikube's docker daemon):

`eval $(minikube docker-env)`

`make images`

## Run system test

