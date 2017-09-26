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

FROM local/urb-bin-base

RUN yum update -y && yum install -y java-1.8.0-openjdk-headless wget && yum clean all

RUN mkdir -p /opt && \
    wget -qO- d3kbcqa49mib13.cloudfront.net/spark-2.1.0-bin-hadoop2.7.tgz | tar xz -C /opt && \
    cp /opt/spark-2.1.0-bin-hadoop2.7/conf/spark-defaults.conf.template /opt/spark-2.1.0-bin-hadoop2.7/conf/spark-defaults.conf && \
    echo "spark.mesos.executor.home /opt/spark-2.1.0-bin-hadoop2.7" >> /opt/spark-2.1.0-bin-hadoop2.7/conf/spark-defaults.conf && \
    mkdir -p /urb/lib

#RUN echo "log4j.logger.org.apache.spark.deploy.mesos=TRACE" >> /opt/spark-2.1.0-bin-hadoop2.7/conf/log4j.properties &&\
#    echo "log4j.logger.org.apache.spark.scheduler.cluster.mesos=TRACE" >> /opt/spark-2.1.0-bin-hadoop2.7/conf/log4j.properties

ENV SPARK_HOME=/opt/spark-2.1.0-bin-hadoop2.7
ENV MESOS_NATIVE_JAVA_LIBRARY=/urb/lib/liburb.so
ENV JAVA_HOME=/etc/alternatives/jre_openjdk
