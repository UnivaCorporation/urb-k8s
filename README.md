# Kubernetes Adapter for Universal Resource Broker (URB)

This project allows one to run [Apache Mesos](http://mesos.apache.org) frameworks with Universal Resource Broker (URB) in a [Kubernetes](https://kubernetes.io) cluster.

It utilizes the [urb-core](https://github.com/UnivaCorporation/urb-core) project and provides the Kubernetes adapter for URB.

Please see the [Universal Resource Broker core](https://github.com/UnivaCorporation/urb-core) project for more architectual details.

## Doing a Quick Trial

In order to do a quick trial there is no need to clone and build a whole project.
There is an installation script which can be downloaded with:

`curl -O https://raw.githubusercontent.com/UnivaCorporation/urb-k8s/master/install/inst_urb.sh && chmod a+x inst_urb.sh`

and used to install URB on existing Kubernetes cluster from pre-built docker images hosted on [DockerHub](https://hub.docker.com/u/univa) and Kubernetes yaml files from this repository. In addtinion to URB service, several ready to use Mesos frameworks (run `./inst_urb.sh --help` for more information) can be installed as well. For example following command will install URB master service, Marathon and Chronos frameworks as well as Spark:

`./inst_urb.sh -c urb,urb-marathon,urb-chronos,urb-spark`

Upon execution of the above command, Marathon and Chronos URLs will be displayed as well as Spark driver pod will become available (see more detailes on running Spark examples below). Local URB configuration file `urb.conf` with custom framework configuration sections for the installed Mesos frameworks can be modified and reloaded as described in _Updating URB configuration_ section.

Above installation can be deleted with following command:

`./inst_urb.sh --remove -c urb,urb-marathon,urb-chronos,urb-spark,urb-zoo`


## Build URB

The following steps need to be done to perform a project build:

## Install `kubectl` and `minikube`

`curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl && chmod a+x kubectl && sudo mv kubectl /usr/local/bin`

`curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 && chmod +x minikube && sudo mv minikube /usr/local/bin`

## Start `minikube`

_Requires Virtualbox or another supported minikube backend to be installed_. _By default minikube virtual machine is configured for 2Gb of memory, which is not enough to run Spark examples, it is recommended to set it at least to 4Gb_.

`minikube start`

## Create Kubernetes Configuration

_This will be used inside the build container_

`tools/vagrant_kube_conf.sh`

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

- As pods within a Kubernetes cluster
- As processes outside of Kubernetes cluster

In both cases the `LD_LIBRARY_PATH` and `MESOS_NATIVE_JAVA_LIBRARY` (for Java or Scala based frameworks) environment variables have to be specified in the run time environment of the framework if it relies on _Mesos native binary API_. `LD_LIBRARY_PATH` has to contain a path to the URB `liburb.so` shared library. `MESOS_NATIVE_JAVA_LIBRARY` should point to the same library file. Different frameworks may have different ways of specifing the Mesos master URI. In general, standard Mesos URI has to be changed to the URB one: `urb://urb-master:6379`.

Frameworks based on v1 Mesos HTTP API do not have any URB binary dependencies and can use `urb-master:5060` connection URI.

### Run Mesos Framework Inside a Kubernetes Cluster

The framework has to be "dockerized" and associated with the corresponding Kubernetes object like pod, deployment, service, etc.
For frameworks based on _Mesos native binary API_, following run time dependencies are required to be installed in the framework Docker container: `libev`, `libuuid`, `zlib` as well as `liburb.so` (found in `urb-core/dist/urb-*-linux-x86_64/lib/linux-x86_64`) and `LD_LIBRARY_PATH` and/or `MESOS_NATIVE_JAVA_LIBRARY` set,  and URB URI specified as `urb://urb-master:6379` (see for example [Marathon](test/marathon/marathon.yaml) service). There are two docker images which can be used as a base for creating custom framework images [urb-bin-base.dockerfile](urb-bin-base.dockerfile) with URB binary dependencies specified above and [urb-python-base.dockerfile](urb-python-base.dockerfile) with added Python dependencies. They are used in following examples: [C++ example framework](test/example-frameworks/cpp-framework.dockerfile), [Python example framework](python-framework.dockerfile).

### Run Mesos Framework From Outside of the Kubernetes Cluster

The URB service exposes two ports for _Native_ and _HTTP APIs_. In the minikube based development environment the URB URIs can be retrieved with: `minikube service urb-master --format "urb://{{.IP}}:{{.Port}}"`. It is crucial to have the framework runtime installed on the same paths inside and outside of the Kubernetes cluster as well as to have URB related paths (`LD_LIBRARY_PATH`, `MESOS_NATIVE_JAVA_LIBRARY`) properly set.

### Using Persistent Volumes or Self Contained Docker Images

In many situations, to access global data or when a framework uses a custom executor or an executor requires a massive run time bundle that is shared by the framework scheduler and executor it is convenient to have a common run time located on a persistent volume that is accessible from both the executor runner and the framework. Persistent volume claims to be used by framework's executor can be configured with `persistent_volume_claims` configuration option in URB configuration file [etc/urb.conf](etc/urb.conf) on per framework basis or in `DefaultFrameworkConfig` section as default value for all frameworks. It allows to place framework or other data files on shared volume within the cluster.

Alternatively, all framework and executor files can be located in corresponding self contained docker images. Such frameworks has to be configured in [etc/urb.conf](etc/urb.conf) with `executor_runner` framework configuration option for custom executor runner docker image which can be based on generic URB executor runner image [urb-executor-runner.dockerfile](urb-executor-runner.dockerfile). See custom executor runner docker image for Python test framework [python-executor-runner.dockerfile](python-executor-runner.dockerfile) for example. 

## Run Mesos Example Frameworks

Mesos and URB projects include several example frameworks such as C++ [example_framework.cpp](urb-core/source/cpp/liburb/test/example_framework.cpp) and Python [test_framework.py](urb-core/source/cpp/liburb/python-bindings/test/test_framework.py) frameworks for demonstration purposes. In order to start these frameworks, the URB service has to be running (`kubectl create -f source/urb-master.yaml`).

Examples below will demonstrate different options for running Mesos frameworks:

- C++ framework runs inside kubernetes cluster, framework executable and custom executor located on shared persistent volume 
- C++ framework executable located and runs outside of the kubernetes cluster and custom executor located on shared persistent volume
- Python framework and custom executor located in self contained docker images

### C++ Example Framework

This C++ example framework relies on both framework and custom executor executables located on persistent volume `example-pv` defined in [pv.yaml](test/example-frameworks/pv.yaml) with corresponding persistent volume claim [pvc.yaml](test/example-frameworks/pvc.yaml). This persistent volume is configured in C++ example framework configuration section `TestFrameworkC*FrameworkConfig` in URB configuration file [etc/urb.conf](etc/urb.conf) in a following way: `persistent_volume_claims = example-pvc:/opt/example` to be accessible from generic URB executor runner. The same persistent volume is used in the job definition for C++ framework: [test/example-frameworks/cpp-framework.yaml](test/example-frameworks/cpp-framework.yaml).

The `run.sh` helper script is designed to allow consecutive runs of the example framework by first cleaning up the Kubernetes cluster from the previous run, creating the persistent volume, starting C++ framework in the minikube environment, and waiting for the completion.  It can be run with the following command:

```
test/example-frameworks/run.sh
```

Assuming that persistent volume is already created by the script, C++ example framework can be started manually:

```
kubectl create -f test/example-frameworks/cpp-framework.yaml
```

The output from the framework can be examined with (the pod name has to be replaced with actual name from your environment):

```
kubectl logs cpp-framework-ck8zz
```


This is an example of how to run the C++ example framework from outside of the Kubernetes cluster (build machine). Since this example framework uses _Native API_ we need to determine URB connection string.

- List the URB service URLs:

```
minikube service urb-master --url"
```

Take an ip address and a port of the one of two URLs printed for which following command fails (use actual ip address and port from previuos command):

```
curl -i --header "Content-Type: application/json" --header "Accept: application/json" -X GET http://192.168.99.100:31607/master/state
```

and form URB connection string similar to `urb://192.168.99.100:31607`. (The URL for which above command succeedeed corresponds to _Mesos v1 HTTP API endpoint_.)

- Login to build machine:

```
cd urb-core/vagrant; vagrant ssh
```
- Create a directory to contain C++ framework binary which matches the path `/opt/example/bin/example_framework.test` in the Kubernetes persistent volume created in minikube by `test/example-frameworks/run.sh` in the previous example:

```
sudo mkdir -p /opt/example/bin
```
- Copy the C++ framework executable:

```
sudo cp /scratch/urb/urb-core/dist/urb-*-linux-x86_64/share/examples/frameworks/linux-x86_64/example_framework.test /opt/example/bin
```
- Run the C++ framework (substitute `<URB_URI>` with an actual URI determined earlier)

```
cd /scratch/urb
LD_LIBRARY_PATH=$(pwd)/urb-core/dist/urb-*-linux-x86_64/lib/linux-x86_64:$LD_LIBRARY_PATH URB_MASTER=<URB_URI> /opt/example/bin/example_framework.test
```

Framework tasks will be submitted to Kubernetes cluster in a same way as in previous example.

### Python Example Framework

With Python example framework both framework scheduler and custom executor will run in self contained docker containers with no relying on the persistent volume. Python framework `test_framework.py` file is added in `/urb/bin` directory in docker image [python-framework.dockerfile](python-framework.dockerfile) based on [urb-python-base.dockerfile](urb-python-base.dockerfile) which includes all required URB binary and Python dependencies. Python example framework job is defined in [test/example-frameworks/python-framework.yaml](test/example-frameworks/python-framework.yaml). Similarly, custom executor runner docker image [python-executor-runner.dockerfile](python-executor-runner.dockerfile) contains custom executor `test_executor.py` file on the same path (`/urb/bin`). This image is based on generic [urb-executor-runner.dockerfile](urb-executor-runner.dockerfile). And framework configurtion section `TestFrameworkPy*FrameworkConfig` for Python example framework in [etc/urb.conf](etc/urb.conf) has `executor_runner = local/python-executor-runner` configuration option which points to custom executor docker image.

Run Python framework example with following command:

```
kubectl create -f test/example-frameworks/python-framework.yaml
```

The output from the framework can be examined with (the pod name has to be replaced with actual name from your environment):

```
kubectl logs python-framework-ck8zz
```


## Run some actual Mesos frameworks

Some Mesos framework schedulers, such as Marathon, Chronos or Singularity have a dependency on [Zookeeper](https://zookeeper.apache.org). Like the C++ and Python example frameworks they can run inside or outside of a Kubernetes cluster submitting their tasks to the Kubernetes cluster.

### Marathon

In this example the [Marathon](https://mesosphere.github.io/marathon) scheduler will be running inside of the Kubernetes cluster. The external project [kubernetes-zookeeper](https://github.com/taeminKwon/kubernetes-zookeeper) is used to install Zookeeper in minikube:

```
kubectl create -f test/marathon/kubernetes-zookeeper-master/zoo-rc.yaml
kubectl create -f test/marathon/kubernetes-zookeeper-master/zoo-service.yaml
```

Create Marathon Docker image. This image is based on mesosphere/marathon image thus URB binary dependencies has to be installed directly with package manager in [test/marathon/marathon.dockerfile](test/marathon/marathon.dockerfile). 

```
cd test/marathon
docker build --rm -t local/marathon -f marathon.dockerfile .
```

Create Marathon Kubernetes service and deployment with [test/marathon/marathon.yaml](test/marathon/marathon.yaml). It relies on persistent volume `urb-pvc` with URB installation located in `/opt/urb` created by helper script in first C++ example.

```
kubectl create -f marathon.yaml
```

Now Marathon scheduler can be accessed from the web browser at:

```
minikube service marathonsvc --url
```

Marathon jobs will be dispatched to minikube Kubernetes cluster.

### Spark

In this section Python _Pi_, _wordcount_ examples and _PySpark Shell_ from the [Spark](https://spark.apache.org) data processing framework will be demonstrated.

#### Spark Python _Pi_ example

From the project root on the host machine run following script:

```
test/spark/run.sh
```

It creates a Spark installation in the persistent volume ([test/spark/pv.yaml](test/spark/pv.yaml)) accessible by both driver and executor sides of the Spark application, creates a Docker container ([test/spark/spark.dockerfile](test/spark/spark.dockerfile)) based on URB binary base image (`urb-bin-base`) and corresponding Kubernetes job ([test/spark/spark.yaml](test/spark/spark.yaml)) which will be used to run driver side of the Spark _Pi_ application. This Spark example will be registered as Mesos framework with name `SparkExamplePi` defined in parameter to `--name` option of `spark-submit` command. Correspondingly `Spark*FrameworkConfig` configuration section in [etc/urb.conf](etc/urb.conf) has to be configured with `persistent_volume_claims = spark-pvc:/opt/spark-2.1.0-bin-hadoop2.7` for generic URB executor runner `urb-executor-runner` to be able to access this persistent volumes.

Upon execution of the script, determine a Spark driver pod name with `kubectl get pods | grep "^spark"`.

Run the Spark _Pi_ example on the pod with the name from the previous command:

```
kubectl exec spark-7g14w -it -- /opt/spark-2.1.0-bin-hadoop2.7/bin/spark-submit --name SparkExamplePi --master mesos://urb://urb-master:6379 /opt/spark-2.1.0-bin-hadoop2.7/examples/src/main/python/pi.py
```

It should produce an output which includes _Pi_ number estimate similar to:

```
Pi is roughly 3.140806
```

#### Spark Python _wordcount_ example

Alternatively, the Spark _wordcount_ example can be run without relying on persistent volume to keep Spark deployment but using custom framework [test/spark/spark-driver.dockerfile](test/spark/spark-driver.dockerfile) and executor runner [test/spark/spark-exec.dockerfile](test/spark/spark-exec.dockerfile) docker images containing Spark run time files with corresponding Kubernetes job [test/spark/spark-driver.yaml](test/spark/spark-driver.yaml) which will be used to run driver side of the Spark _wordcount_ application. This example requires some input text file (for example current `README.md` file) which will be located on separate persistent volume [test/spark/scratch-pv.yaml](test/spark/scratch-pv.yaml) (created in previous example by `test/spark/run.sh` script). The `spark-submit` command will have `--name CustomWordCount` parameter so `Custom*FrameworkConfig` framework configuration section of [etc/urb.conf](etc/urb.conf) file has to be configured for persistent volume claim `scratch-pvc` and custom executor runner docker image `local/spark-exec` with:

```
executor_runner = local/spark-exec
persistent_volume_claims = scratch-pvc:/scratch
```

Create docker images running following commands on the host machine:

```
cd test/spark
docker build --rm -t local/spark-driver -f spark-driver.dockerfile .
docker build --rm -t local/spark-exec -f spark-exec.dockerfile .
```

Create Spark driver job in Kubernetes cluster from the root of the project:

```
kubectl create -f spark-driver.yaml
```

Determine a Spark driver pod name with `kubectl get pods | grep spark-driver`.

Run Spark _wordcount_ example using previously determined Spark driver pod name:

```
kubectl exec spark-driver-7g14w -it -- /opt/spark-2.1.0-bin-hadoop2.7/bin/spark-submit --name CustomWordCount --master mesos://urb://urb-master:6379 /opt/spark-2.1.0-bin-hadoop2.7/examples/src/main/python/wordcount.py file:///scratch/README.md
```

It should produce an output with the list of the words and a number of occurances in `README.md` file.

#### PySpark Shell example

Following command will start Python Spark Shell with 4 as a total amount of cores which can be used by all executors for this interactive session:

```
kubectl exec spark-driver-7g14w -it -- /opt/spark-2.1.0-bin-hadoop2.7/bin/pyspark --master mesos://urb://urb-master:6379 --total-executor-cores 4
```

Python Spark Shell uses `PySparkShell` framework name to register, thus taking configuration from `PySparkShellFrameworkConfig` section of URB configuration file [etc/urb.conf](etc/urb.conf) and being able to access persistent volume `scratch-pc` for data store. Now some Spark action can be executed, for example:

```
>>> rdd = sc.textFile('/scratch/README.md')
>>> rdd.collect()
```

### Singularity

[Singularity](http://getsingularity.com) framework takes advantage of _Mesos v1 HTTP API_ so it doesn't have any URB binary dependencies and can be started using following service and deployment based on stock Singularity docker image:

```
kubectl create -f test/singularity/urb-singularity.yaml
```

Access Singularity Web interface at:

```
minikube service urb-singularity --format "http://{{.IP}}:{{.Port}}/singularity"
```

## Updating URB configuration

URB configuration file [etc/urb.conf](etc/urb.conf) consists of multiple configuration settings documented inside a file. Most commonly frameworks configurations and URB service logging levels would be modified. After modification, URB configuration can be reloaded with:

```
kubectl create configmap urb-config --from-file=etc/urb.conf --dry-run -o yaml | kubectl replace -f -
```
