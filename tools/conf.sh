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

set -x

mkdir -p urb-core/vagrant/.minikube
cp ~/.minikube/apiserver.* urb-core/vagrant/.minikube
cp ~/.minikube/ca.* urb-core/vagrant/.minikube
cp ~/.minikube/client.* urb-core/vagrant/.minikube
cp ~/.minikube/cert.pem urb-core/vagrant/.minikube
mkdir -p urb-core/vagrant/.kube
cp ~/.kube/config urb-core/vagrant/.kube/config.orig
sed "s|/home/.*/\.minikube|/vagrant/.minikube|; s|/Users/.*/\.minikube|/vagrant/.minikube|" \
	urb-core/vagrant/.kube/config.orig > urb-core/vagrant/.kube/config
