# Kubernetes adapter for Universal Resource Broker (URB)

This project allows one to run [Apache Mesos](http://mesos.apache.org) frameworks with Universal Resource Broker in [Kubernetes](https://kubernetes.io) cluster.

It utilizes [urb-core](https://github.com/UnivaCorporation/urb-core) project and provides Kubernetes adapter for URB.

Please see [Universal Resource Broker core](https://github.com/UnivaCorporation/urb-core) project for more architectual details.

Following steps need to be done to perform a project build:

## Install `kubectl` and `minikube` (requires `VirtualBox` to be installed):

`curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl && chmod a+x kubectl && sudo mv kubectl /usr/local/bin`
`curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 && chmod +x minikube && sudo mv minikube /usr/local/bin`

## Start `minikube`

`minikube start`

## Create kubernetes configuration to be used inside the build container

`./conf.sh`

## Create docker build environment (requires `docker` to be installed):

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

In both cases `LD_LIBRARY_PATH` and `MESOS_NATIVE_JAVA_LIBRARY` (for Java or Scala based frameworks) environment variables has to be specified for the run time environment of the framework. `LD_LIBRARY_PATH` has to contain a path to URB `liburb.so` shared library. `MESOS_NATIVE_JAVA_LIBRARY` should point to the same library file. Different frameworks may have different ways of specifing Mesos master URI. In general, standard Mesos URI has to be changed to the URB one: `urb://urb-master:6379` .

### Run Mesos framework inside kubernetes cluster

Framework has to be "dockerized" and associated with corresponding kubernetes object like pod, deployment, service, etc.
Following run time dependencied are required to be installed in docker container for the framework: `libev`, `libuuid`, `zlib` as well as `liburb.so` (to be found in `urb-core/dist/urb-*-linux-x86_64/lib/linux-x86_64`) and `LD_LIBRARY_PATH` and/or `MESOS_NATIVE_JAVA_LIBRARY` set (see for example [C++ example framework](cpp-framework.dockerfile), [Python example framework](python-framework.dockerfile), [Marathon](test/marathon/marathon.dockerfile)) and URB URI specified as `urb://urb-master.default:6379` (see for example [Marathon](test/marathon/marathon.yaml)).

In many situations, especially when framework uses custom executor or executor requires massive run time which is shared by framework scheduler and executor, it is convenient to have common run time located on persistent volume which is accessable from executor runner and framework. `urb-pvc` persistent volume claim name is predefined and mounted to `/opt` by URB executor runner making possible to place framework files to this location and share them within the cluster.

### Run Mesos framework from outside of the kubernetes cluster

URB service can be accessable from outside of the cluster on port `30379`. In the development environment with minikube URB URI
can be retrieved with: `minikube service urb-master --format "urb://{{.IP}}:{{.Port}}"`. It is crucial to have framework runtime installed on the same paths inside and outside of kubernetes cluster as well as to have same URB related paths (`LD_LIBRARY_PATH`, `MESOS_NATIVE_JAVA_LIBRARY`) properly set. Since URB executor runner relies on `/opt` path possibly mounted to the persistent volume, it can be used as a base for the frameworks installation outside of the kubernetes cluster.

## Run C++ and Python example frameworks

In order to run C++ and Python example frameworks inside kubernetes cluster:

- URB service has to be running (`kubectl create -f source/urb-master.yaml`),
- persistent volume keeping custom executors has to be created in minikube,
- example frameworks started:

```
    kubectl create -f test/example-frameworks/cpp-framework.yaml
    kubectl create -f test/example-frameworks/python-framework.yaml
```
- an output from the frameworks can be examined with (actual pod names has to be specified):

```
    kubectl logs cpp-framework-ck8zz
    kubectl python-framework-f537l
```

In order to cleans kubernetes cluster from previous run, create persistent volume, start both frameworks in minikube environment and wait for the completionrun run:

```
test/example-frameworks/run.sh
```


This is an example of how to run C++ example framework from the outside of the kubernetes cluster (build machine).

- get URB service URI:

```
    minikube service urb-master --format "urb://{{.IP}}:{{.Port}}"
```
- login to build machine:

```
    cd urb-core/vagrant; vagrant ssh
```
- create directory to contain C++ framework binaries (framework scheduler and executor) which matches path in kubernetes persistent volume:

```
    sudo mkdir -p /opt/bin
```
- copy C++ framework binaries:

```
    sudo cp urb-core/dist/urb-*-linux-x86_64/share/examples/frameworks/linux-x86_64/example_*.test /opt/bin
```
- run C++ framework (substitute `<URB_URI>` with an actual URI determined in the first step from the host machine)

```
    LD_LIBRARY_PATH=$(pwd)/urb-core/dist/urb-*-linux-x86_64/lib/linux-x86_64:$LD_LIBRARY_PATH URB_MASTER=<URB_URI> /opt/bin/example_framework.test
```

## Run some actual Mesos frameworks

Some Mesos framework schedulers such as Marathon or Chronos have dependency on [Zookeeper](https://zookeeper.apache.org). Same as with C++ and Python example frameworks they can run inside of outside of kubernetes cluster submitting their tasks to kubernetes cluster.

### Marathon

In this example Marathon scheduler will be running inside kubernetes cluster. External project [kubernetes-zookeeper](https://github.com/taeminKwon/kubernetes-zookeeper) is used to install Zookeeper in minikube:

```
kubectl create -f test/marathon/kubernetes-zookeeper-master/zoo-rc.yaml
kubectl create -f test/marathon/kubernetes-zookeeper-master/zoo-service.yaml
```

Create Marathon docker image:

```
cd test/marathon
docker build --rm -t local/marathon -f marathon.dockerfile .
```

Create Marathon service and deployment:

```
kubectl create -f marathon.yaml
```

Now Marathon scheduler can be accessed at:

```
minikube service marathonsvc --url
```

### Chronos

Chronos scheduler also requires Zookeeper so we assume that it continues to run after previous example. In this example Chronos will be running in build machine (outside of kubernetes cluster) and dispatch tasks to kubernetes cluster:

- get URB service URI and Zookkeper URL from host machine:

```
    minikube service urb-master --format "urb://{{.IP}}:{{.Port}}"
    minikube service zoo-svc --format "{{.IP}}:{{.Port}}"
```

- add port forwarding in `urb-core/vagrant/Vagrantfile` to build machine for Chronos to be accessable from the host browser by inserting following line after `Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|`:

```
config.vm.network "forwarded_port", guest: 4040, host: 4040
```
- recreate build machine by:

```
    cd urb-core/vagrant
    vagrant destroy -f
    SYNCED_FOLDER=../.. vagrant up
```
- login to build machine:

```
    vagrant ssh
```
- install Chronos and disable it from starting automatically:

```
    sudo rpm -Uvh http://repos.mesosphere.io/el/7/noarch/RPMS/mesosphere-el-repo-7-1.noarch.rpm
    sudo yum install -y chronos
    sudo systemctl stop chronos
    sudo systemctl disable chronos
```
- Start Chronos (substitute `<URB_URI>` and `<ZOO_URL>` with the onces determined in the first step from the host machine):

```
    sudo MESOS_NATIVE_JAVA_LIBRARY=$(echo $(pwd)/urb-core/dist/urb-*-linux-x86_64/lib/linux-x86_64/liburb.so) chronos -u $USER --master <URB_URI> --zk_hosts <ZOO_URL>
```
Now Chronos scheduler can be accessed at `localhost:4040`

### Spark
