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

# install easy_install and pip
RUN yum update -y; yum install -y python-setuptools python-pip; yum clean all

# copy Python packages
COPY urb-core/dist/urb-*-py2.7/*.[we][gh][gl] /tmp/
COPY urb-core/dist/urb-*-py2.7-redhat_7-linux-x86_64/*.[we][gh][gl] /tmp/
COPY urb-core/dist/urb-*/pkg/urb-*-py2.7.[we][gh][gl] /tmp/

# install all required Python dependencies, Mesos eggs
RUN pip install  /tmp/six-*.whl /tmp/click-*.whl && \
    easy_install /tmp/itsdangerous-*.egg /tmp/MarkupSafe-*.egg && \
    pip install  /tmp/Jinja2-*.whl /tmp/Werkzeug-*.whl && \
    easy_install /tmp/google_common-*-py2.7.egg \
                 /tmp/protobuf-*.egg \
                 /tmp/xmltodict-*-py2.7.egg \
                 /tmp/sortedcontainers-*-py2.7.egg \
                 /tmp/redis-*-py2.7.egg \
                 /tmp/pymongo-*-py2.7-linux-x86_64.egg \
                 /tmp/greenlet-*-py2.7-linux-x86_64.egg \
                 /tmp/inotifyx-*-py2.7-linux-x86_64.egg \
                 /tmp/gevent-*-py2.7-linux-x86_64.egg \
                 /tmp/gevent_inotifyx-*-py2.7.egg \
                 /tmp/Flask-*.egg \
                 /tmp/mesos.interface-*-py2.7.egg \
                 /tmp/mesos.scheduler-*-py2.7-linux-x86_64.egg \
                 /tmp/mesos.executor-*-py2.7-linux-x86_64.egg \
                 /tmp/mesos.native-*-py2.7.egg \
                 /tmp/mesos-*-py2.7.egg \
                 /tmp/urb-*-py2.7.egg
 
