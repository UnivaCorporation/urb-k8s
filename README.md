# Introduction

Universal Resource Broker (URB) provides an API for developing and running distributed applications. It's pluggable architecture allows to leverages different cluster resource schedulers as a back end. It supports existing applications developed against the Apache Mesos API. Universal Resource Broker is an enterprise ready application engine for your datacenter.

# Functionality

Universal Resource Broker software provides the following high level functionality:

- Complete _Scheduler_ and _Executor_ API's for building distributed applications. URB supports applications written in C++, Java, Scala, and Python.
- Application _Frameworks_ implement the _Scheduler API_ and start _Executors_ on offered resources from URB.
- _Executors_ implement the _Executor API_ and perform the actual work required by the application.
- Ability to run existing Apache Mesos Frameworks without requiring any modifications.
- Ability to integrate with different resource schedulers by implementing adapter interface for all resource allocation, scheduling, access control, and policy decisions.
- Ability to integrate with different database backends to store historical information about the workloads (MongoDB is interfaced by default, requires external Mongo server)
- Provides unified environment for the back end scheduler and Apache Mesos workloads in the cluster:
    - Single resource pool
    - Single accounting and reporting database
    - Single scheduler configuration interface
- Configurable for High Availability support with automatic service failover

The URB is compartible with Linux, Solaris and other Unix like operating systems.

# Build

Docker has to be installed since project is built in docker Centos 7 environment.

Please read [vagrant/README.md](vagrant/README.md) file in urb-core/vagrant directory for build instructions.

# Usage

This project includes Universal Resource Broker core components. For the Universal Resource Broker to be fully functioning the scheduler back end adapter has to be implemented in Python, based on interface located in source/python/urb/adapters/adapter_interface.py

Structurally it is recommended to create a separate project with adapter interface implementation and use urb-core as an external dependency (similarly to urb-k8s project).

