# Kubernetes Adapter for Universal Resource Broker (URB)

This project allows one to run [Apache Mesos](http://mesos.apache.org) frameworks with Universal Resource Broker (URB) in a [Kubernetes](https://kubernetes.io) cluster.

It utilizes the [urb-core](https://github.com/UnivaCorporation/urb-core) project and provides the Kubernetes adapter for URB.

Please see the [Universal Resource Broker core](https://github.com/UnivaCorporation/urb-core) project for more architectual details.

The following steps need to be done to perform a project build:

## Install `kubectl` and `minikube`

`curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl && chmod a+x kubectl && sudo mv kubectl /usr/local/bin`

`curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 && chmod +x minikube && sudo mv minikube /usr/local/bin`

## Start `minikube`

_Requires Virtualbox or another supported minikube backend to be installed_

`minikube start`

## Create Kubernetes Configuration

_This will be used inside the build container_

`tools/conf.sh`

## Create Docker Build Environment
_Requires `docker` to be installed_

`cd urb-core/vagrant`

`make`

## Start Docker Build Container

`SYNCED_FOLDER=../.. vagrant up --provider=docker`

## Login Into Docker Build Container

_Enter the build container_

`vagrant ssh`

### Install `kubectl`:

`curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl && chmod a+x kubectl && sudo mv kubectl /usr/local/bin`

### Build

`cd /scratch/urb`

`make`

### Test

`export KUBECONFIG=/vagrant/.kube/config`

`kubectl proxy&`

`make test`

### Create Distribution Artifacts

`make dist`

## Create Docker Images for URB Service and Example Frameworks

_Open a new shell in the root of the project and run:_

`eval $(minikube docker-env)`

`make images`

## Run Mesos Frameworks

URB service in minikube Kubernetes cluster can be started by creating first _ConfigMap_ with URB configuration:

`kubectl create configmap urb-config --from-file=etc/urb.conf`

and creating URB service deployment with following command:

`kubectl create -f source/urb-master.yaml`

There are two options to run Mesos framework schedulers: 

* As pods within a Kubernetes cluster
* As processes outside of Kubernetes cluster

In both cases the `LD_LIBRARY_PATH` and `MESOS_NATIVE_JAVA_LIBRARY` (for Java or Scala based frameworks) environment variables have to be specified in the run time environment of the framework. `LD_LIBRARY_PATH` has to contain a path to the URB `liburb.so` shared library. `MESOS_NATIVE_JAVA_LIBRARY` should point to the same library file. Different frameworks may have different ways of specifing the Mesos master URI. In general, standard Mesos URI has to be changed to the URB one: `urb://urb-master:6379`.

### Run Mesos Framework Inside a Kubernetes Cluster

The framework has to be "dockerized" and associated with the corresponding Kubernetes object like pod, deployment, service, etc.
The following run time dependencies are required to be installed in the framework Docker container: `libev`, `libuuid`, `zlib` as well as `liburb.so` (found in `urb-core/dist/urb-*-linux-x86_64/lib/linux-x86_64`) and `LD_LIBRARY_PATH` and/or `MESOS_NATIVE_JAVA_LIBRARY` set (see for example [C++ example framework](cpp-framework.dockerfile), [Python example framework](python-framework.dockerfile), [Marathon](test/marathon/marathon.dockerfile)) and URB URI specified as `urb://urb-master.default:6379` (see for example [Marathon](test/marathon/marathon.yaml)).

In many situations, especially when a framework uses a custom executor or an executor requires a massive run time bundle that is shared by the framework scheduler and executor it is convenient to have a common run time located on a persistent volume that is accessible from both the executor runner and the framework. The `urb-pvc` persistent volume claim name is predefined and mounted to `/opt` by the URB executor runner making it possible to place framework or other data files in this location to be shared within the cluster.

### Run Mesos Framework From Outside of the Kubernetes Cluster

The URB service can be accessible from outside of the cluster at port `30379`. In the minikube based development environment the URB URI can be retrieved with: `minikube service urb-master --format "urb://{{.IP}}:{{.Port}}"`. It is crucial to have the framework runtime installed on the same paths inside and outside of the Kubernetes cluster as well as to have URB related paths (`LD_LIBRARY_PATH`, `MESOS_NATIVE_JAVA_LIBRARY`) properly set. Since the URB executor runner relies on the `/opt` path possibly mounted to the persistent volume, it can be used as a base for framework installations outside of the Kubernetes cluster.

## Run C++ and Python Example Frameworks

In order to run C++ and Python example frameworks inside the Kubernetes cluster:

- The URB service has to be running (`kubectl create -f source/urb-master.yaml`)
- A persistent volume for storing custom executors has to be created in minikube
- The appropriate example frameworks need to be started:

```
    kubectl create -f test/example-frameworks/cpp-framework.yaml
    kubectl create -f test/example-frameworks/python-framework.yaml
```
- The output from the frameworks can be examined with (replace pod names with names from your environment):

```
    kubectl logs cpp-framework-ck8zz
    kubectl logs python-framework-f537l
```

The `run.sh` helper script is designed to allow consecutive runs of the example frameworks by first cleaning up the Kubernetes cluster from the previous run, creating the persistent volume, starting both frameworks in the minikube environment, and waiting for the completion of the frameworks.  It can be run with the following command:

```
test/example-frameworks/run.sh
```


This is an example of how to run the C++ example framework from outside of the Kubernetes cluster (build machine).

- Get the URB service URI:

```
    minikube service urb-master --format "urb://{{.IP}}:{{.Port}}"
```
- Login to build machine:

```
    cd urb-core/vagrant; vagrant ssh
```
- Create a directory to contain C++ framework binaries (framework scheduler and executor) which matches the path in the Kubernetes persistent volume [test/example-frameworks/pv.yaml](test/example-frameworks/pv.yaml) created in minikube at `/urb` path by [test/example-frameworks/run.sh](test/example-frameworks/run.sh) in the previous example:

```
    sudo mkdir -p /opt/bin
```
- Copy the C++ framework binaries:

```
    sudo cp urb-core/dist/urb-*-linux-x86_64/share/examples/frameworks/linux-x86_64/example_*.test /opt/bin
```
- Run the C++ framework (substitute `<URB_URI>` with an actual URI determined in the first step from the host machine)

```
    LD_LIBRARY_PATH=$(pwd)/urb-core/dist/urb-*-linux-x86_64/lib/linux-x86_64:$LD_LIBRARY_PATH URB_MASTER=<URB_URI> /opt/bin/example_framework.test
```

## Run some actual Mesos frameworks

Some Mesos framework schedulers, such as Marathon or Chronos, have a dependency on [Zookeeper](https://zookeeper.apache.org). Like the C++ and Python example frameworks they can run inside or outside of a Kubernetes cluster submitting their tasks to the Kubernetes cluster.

### Marathon

In this example the [Marathon](https://mesosphere.github.io/marathon) scheduler will be running inside of the Kubernetes cluster. The external project [kubernetes-zookeeper](https://github.com/taeminKwon/kubernetes-zookeeper) is used to install Zookeeper in minikube:

```
kubectl create -f test/marathon/kubernetes-zookeeper-master/zoo-rc.yaml
kubectl create -f test/marathon/kubernetes-zookeeper-master/zoo-service.yaml
```

Create Marathon Docker image:

```
cd test/marathon
docker build --rm -t local/marathon -f marathon.dockerfile .
```

Create Marathon service and deployment:

```
kubectl create -f marathon.yaml
```

Now Marathon scheduler can be accessed from the web browser at:

```
minikube service marathonsvc --url
```

### Spark

In this section Python Pi example from the [Spark](https://spark.apache.org) data processing framework will be run inside a Kubernetes cluster.

From the project root run following script:

```
test/spark/run.sh
```

It creates a Spark deployment in the persistent volume, creates a Docker container and corresponding Kubernetes job, and creates a persistent volume object that can be used to run both driver and executor sides of the Spark application. Upon its execution determine a Spark pod name with `kubectl get pods`.

Run the Spark Pi example on the pod with the name from the previous command:

```
kubectl exec spark-7g14w -it -- /opt/spark-2.1.0-bin-hadoop2.7/bin/spark-submit --name SparkExamplePi --master mesos://urb://urb-master:6379 /opt/spark-2.1.0-bin-hadoop2.7/examples/src/main/python/pi.py
```

It should produce an output which includes Pi number estimate similar to:

```
Pi is roughly 3.140806
```

Alternatively, the same Spark Pi example can be run without relying on persistent volume to keep Spark deployment but using custom executor runner with Spark run time files.

Docker file for Spark custom executor runner [test/spark/spark-exec.dockerfile](test/spark/spark-exec.dockerfile) is based on generic [urb-executor-runner.dockerfile](urb-executor-runner.dockerfile) and uses the same `/opt` directory as root for Spark deployment.

Create docker image running following commands on the host:

```
cd test/spark
docker build --rm -t local/spark-exec -f spark-exec.dockerfile .
```

Run the Spark Pi example using previously determined URB master connection string and different application name `PythonPi`:

```
kubectl exec spark-7g14w -it -- /opt/spark-2.1.0-bin-hadoop2.7/bin/spark-submit --name PythonPi --master mesos://urb://urb-master:6379 /opt/spark-2.1.0-bin-hadoop2.7/examples/src/main/python/pi.py
```

Spark application name `PythonPi` provided as a parameter is used by Spark as Mesos framework name, driver registers with. This name will prompt URB to use `Python*FrameworkConfig` framework configuration from [etc/urb.conf](etc/urb.conf) with `executor_runner = local/spark-exec` configuration option pointing to Spark custom executor runner docker image created earlier. Note that in this example Spark driver running on `spark-7g14w` pod still uses Spark deployment located on `urb-pv` persistent volume but Spark executors use thier own local Spark deployments.

## Updating URB configuration

URB configuration file [etc/urb.conf](etc/urb.conf) consists of multiple configuration settings documented inside a file. Most commonly frameworks configurations and URB service logging levels would be modified. After modification, URB configuration can be reloaded with:

```
kubectl create configmap urb-config --from-file=etc/urb.conf --dry-run -o yaml | kubectl replace -f -
```
