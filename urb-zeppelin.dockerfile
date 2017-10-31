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

FROM apache/zeppelin:0.7.2

RUN apt-get update && apt-get install -y libev4 libuuid1 zlib1g wget && apt-get clean

RUN mkdir -p /opt && \
    wget -qO- d3kbcqa49mib13.cloudfront.net/spark-2.1.0-bin-hadoop2.7.tgz | tar xz -C /opt && \
    cp /opt/spark-2.1.0-bin-hadoop2.7/conf/spark-defaults.conf.template /opt/spark-2.1.0-bin-hadoop2.7/conf/spark-defaults.conf && \
    echo "spark.mesos.executor.home /opt/spark-2.1.0-bin-hadoop2.7" >> /opt/spark-2.1.0-bin-hadoop2.7/conf/spark-defaults.conf

ENV SPARK_HOME=/opt/spark-2.1.0-bin-hadoop2.7

# set environment variables, copy binaries
ENV URB_ROOT=/urb
RUN mkdir -p $URB_ROOT/lib
COPY urb-core/dist/urb-*-linux-x86_64/lib/linux-x86_64/liburb*.so.*.*.* $URB_ROOT/lib/
RUN ["/bin/bash", "-c", "cd $URB_ROOT/lib; for l in liburb*; do ll=${l}_; ln -s $l ${ll/.[0-9].[0-9]_/}; ln -s $l ${l/.[0-9].[0-9].[0-9]/}; done"]
ENV LD_LIBRARY_PATH=$URB_ROOT/lib:$LD_LIBRARY_PATH
ENV MESOS_NATIVE_JAVA_LIBRARY=$URB_ROOT/lib/liburb.so

EXPOSE 8080

