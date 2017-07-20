#!/usr/bin/env python

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

if __name__ == '__main__':
    # add path to urb
    import sys
    sys.path.append('../../../urb-core/source/python')

from urb.log.log_manager import LogManager
from urb.config.config_manager import ConfigManager
from urb.exceptions.unknown_job import UnknownJob
from urb.exceptions.completed_job import CompletedJob
from urb.utility.value_utility import ValueUtility
import gevent
import uuid
import os
import copy
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import yaml


class K8SAdapter(object):
    """ Kubernetes Adapter class. """

    CONFIG_MAP_DEL_WAIT = 10.0
    URB_EXECUTOR_RUNNER = "urb-executor-runner"
    CONFIG_MAP_TEMPLATE = URB_EXECUTOR_RUNNER + "-config"
    JOB_NAME_MAX_SIZE = 63
    UUID_SIZE = 8

    def __init__(self, k8s_registry_path = ""):
        self.logger = LogManager.get_instance().get_logger(
            self.__class__.__name__)
        self.logger.info("K8s registry path: %s" % k8s_registry_path)
        self.configure()
        self.channel_name = None
        with open(os.path.join(os.path.dirname(__file__), K8SAdapter.CONFIG_MAP_TEMPLATE + ".yaml")) as fc:
            self.config_map = yaml.load(fc)
            self.logger.debug("Loaded config map yaml: %s" % self.config_map)
        with open(os.path.join(os.path.dirname(__file__), K8SAdapter.URB_EXECUTOR_RUNNER + ".yaml")) as fj:
            self.job = yaml.load(fj)
            if len(k8s_registry_path) != 0:
                self.job['spec']['template']['spec']['containers'][0]['image'] = k8s_registry_path + "/" + K8SAdapter.URB_EXECUTOR_RUNNER
            self.logger.debug("Loaded job yaml: %s" % self.job)
            self.job_name_template = self.job['metadata']['name']
            # uuid.time_low size is 8, plus 2 dashes ('-')
            self.job_name_template_size = len(self.job_name_template) + K8SAdapter.UUID_SIZE + 2
            if self.job_name_template_size >= K8SAdapter.JOB_NAME_MAX_SIZE:
                self.logger.error("Job name template %s is too long, should be < %s bytes" %
                                  (self.job_name_template_size, K8SAdapter.JOB_NAME_MAX_SIZE))
        self.core_v1 = client.CoreV1Api()
        self.batch_v1 = client.BatchV1Api()
        self.config_map_dict = {}

    def configure(self):
        cm = ConfigManager.get_instance()
        # we might want to get namespace from config or name it after framework
        self.namespace = "default"
        # cover test environment
        if __name__ == '__main__' or \
          'KUBERNETES_SERVICE_HOST' not in os.environ or \
          'KUBERNETES_SERVICE_PORT' not in os.environ:
            client.Configuration().host = "http://127.0.0.1:8001"
#            config.load_kube_config()
        else:
            # to workaround for:
            # SSLError hostname '10.0.0.1' doesn't match either of 'kubernetes.default.svc.cluster.local', 'kubernetes.default.svc', 'kubernetes.default', 'kubernetes'
            # https://github.com/kubernetes-incubator/client-python/issues/254
            # has to set environment variable:
            os.environ['KUBERNETES_SERVICE_HOST'] = 'kubernetes'
            config.load_incluster_config()

    # override default executor runner command (for testing purposes)
    def set_command(self, cmd = ["/bin/sh", "-c", "env; sleep 1"]):
        self.job['spec']['template']['spec']['containers'][0]['command'] = cmd
        
    def set_channel_name(self, channel_name):
        self.channel_name = channel_name

    def authenticate(self, request):
        self.logger.trace("Authenticate: %s" % request)

    def deactivate_framework(self, request):
        self.logger.trace("Deactivate framework: %s" % request)

    def exited_executor(self, request):
        self.logger.trace("Exited executor: %s" % request)

    def kill_task(self, request):
        self.logger.trace("Kill task: %s" % request)

    def launch_tasks(self, framework_id, tasks, *args, **kwargs):
        self.logger.trace("Launch tasks for framework id: %s" % framework_id)
#        self.logger.trace("Launch tasks for framework id: %s" % framework_id['value'])

    def reconcile_tasks(self, request):
        self.logger.trace("Reconcile tasks: %s" % request)
        # indicate that job status reasonably can be retrieved on adapter level (get_job_status)
        return True

    def register_executor_runner(self, framework_id, slave_id, *args, 
            **kwargs):
        self.logger.trace(
            "Register executor runner for framework id %s, slave id %s" %
            (framework_id, slave_id))

    def register_framework(self, max_tasks, concurrent_tasks, framework_env, user=None, *args, **kwargs):
        job_ids = self.submit_jobs(max_tasks, concurrent_tasks, framework_env, user, args, kwargs)
        return job_ids

    def __add_config_map(self, framework_id):
        if framework_id not in self.config_map_dict:
            self.__create_config_map(framework_id)
            self.config_map_dict[framework_id] = copy.deepcopy(self.config_map)

    def __delete_config_map(self, framework_id):
        try:
            fid = self.config_map_dict.get(framework_id)
            if fid is None:
                self.logger.warn("Cannot delete config map: no element with id: %s" % framework_id)
                return
            name = fid['metadata']['name']
            body = client.V1DeleteOptions()
            resp = self.core_v1.delete_namespaced_config_map(name = name,
                                                             namespace = self.namespace,
                                                             body = body,
                                                             grace_period_seconds = 0)
        except ApiException as e:
            self.logger.error("ApiException deleting config map %s: %s" % (name, e))

        del self.config_map_dict[framework_id]

    def __create_config_map(self, framework_id = None):
        if framework_id:
            self.config_map['metadata']['name'] = K8SAdapter.CONFIG_MAP_TEMPLATE + "-" + framework_id
            self.config_map['data']['URB_FRAMEWORK_ID'] = framework_id
        try:
            self.logger.info("Creating config map: %s" % self.config_map['metadata']['name'])
            config_map_resp = self.core_v1.create_namespaced_config_map(body = self.config_map,
                                                                        namespace = self.namespace)
            self.logger.trace("Config map created: %s" % self.config_map['metadata']['name'])
        except ApiException as e:
            self.logger.debug("ApiException creating config map: %s" % e)
            if e.reason == "Conflict":
                self.logger.info("Delete existing config map: %s" % self.config_map['metadata']['name'])
                try:
                    body = client.V1DeleteOptions()
                    resp = self.core_v1.delete_namespaced_config_map(name = self.config_map['metadata']['name'],
                                                                namespace = self.namespace,
                                                                body = body,
                                                                grace_period_seconds = 0)
                except ApiException as ee:
                    self.logger.error("ApiException deleting config map: %s" % ee)
                try:
                    self.logger.info("Creating new config map: %s" % self.config_map['metadata']['name'])
                    resp = self.core_v1.create_namespaced_config_map(body = self.config_map,
                                                                     namespace = self.namespace)     
                    self.logger.trace("New config map created: %s" % self.config_map['metadata']['name'])
                except ApiException as ee:
                    self.logger.error("ApiException creating config map again: %s" % ee)
                    raise ee
            else:
                self.logger.error("ApiException creating config map with reason other than Conflict: %s" % e)
                raise e
#        except TIMEO
        except Exception as ge:
            self.logger.error("Exception creating config map: %s" % ge)
            raise ge

    def submit_jobs(self, max_tasks, concurrent_tasks, framework_env, user=None, *args, **kwargs):
        self.logger.debug("register_framework: max_tasks=%s, concurrent_tasks=%s, framework_env=%s, user=%s, kwargs: %s" %
                         (max_tasks, concurrent_tasks, framework_env, user, kwargs))

        self.__add_config_map(framework_env['URB_FRAMEWORK_ID'])
        framework_name = framework_env['URB_FRAMEWORK_NAME'].lower()
        # try not to exceed name limit in 63 bytes
        left = K8SAdapter.JOB_NAME_MAX_SIZE - self.job_name_template_size
        if len(framework_name) > left:
            framework_name = framework_name[:left]
        job_name = "%s-%s-%s" % (self.job_name_template, framework_name, uuid.uuid1().hex[:K8SAdapter.UUID_SIZE])
        job_ids = []
        for i in range(0,concurrent_tasks):
            if i >= max_tasks:
                break
            self.job['metadata']['name'] = job_name
            self.job['spec']['template']['spec']['containers'][0]['envFrom'][0]['configMapRef']['name'] = \
                                 K8SAdapter.CONFIG_MAP_TEMPLATE + "-" + framework_env['URB_FRAMEWORK_ID']
            self.logger.info("Submit k8s job: %s" % self.job['metadata']['name'])
            self.logger.debug("With config map ref: %s" % self.job['spec']['template']['spec']['containers'][0]['envFrom'][0]['configMapRef']['name'])
            job_resp = self.batch_v1.create_namespaced_job(body = self.job, namespace = self.namespace)
            self.logger.trace("job_resp: %s" % job_resp)
            uid = job_resp.metadata.uid
            label_selector = "controller-uid=" + uid
            list_resp = self.core_v1.list_namespaced_pod(namespace = self.namespace,
                                                         label_selector = label_selector)
            self.logger.trace("list_resp: %s" % list_resp)
            items = len(list_resp.items)
            if items > 1:
                self.logger.warn("Only one element expected in pod list for label selector: %s" % label_selector)
            elif items == 0:
                self.logger.error("No elements in pod list for label selector: %s" % label_selector)
                continue
            pod_name = list_resp.items[0].metadata.name
            # job id is set as pod name as it can be exposed as JOB_ID environment variable mapped from
            # metadata.name to executor runner
            job_id = (pod_name,None,None)
            self.logger.info("Submitted job to k8s, got pod id: %s, uid=%s" % (pod_name, uid))
            job_ids.append(job_id)

        return job_ids

    def register_slave(self, request):
        self.logger.trace("Register slave: %s" % request)

    def reregister_framework(self, request):
        self.logger.trace("Reregister framework: %s" % request)

    def reregister_slave(self, request):
        self.logger.trace("Reregister slave: %s" % request)

    def resource_request(self, request):
        self.logger.trace("Resource request: %s" % request)

    def revive_offers(self, request):
        self.logger.trace("Revive offers: %s" % request)

    def submit_scheduler_request(self, request):
        self.logger.trace("Submit scheduler request: %s" % request)

    def status_update_acknowledgement(self, request):
        self.logger.trace("Status update acknowledgement: %s" % request)

    def status_update(self, request):
        self.logger.trace("Status update: %s" % request)

    def scale(self, framework, count):
        self.logger.trace("Scale: framework: %s, count: %s" % (framework, count))

    def unregister_framework(self, framework):
        self.logger.debug("Unregister framework: %s" % framework['id']['value'])
        self.delete_jobs_delay(framework)

    def delete_jobs_delay(self, framework):
        # Delete all of the jobs
        job_ids = framework.get('job_ids')
        if job_ids is not None:
            # Spawn job to make sure the actual executors exit...
            gevent.spawn(self.delete_jobs, job_ids, framework['id']['value'])

    # delete config_map with delay since some pods still might be in creation
    # and to avoid "configmaps not found" message in "kubectl get pods"
    def __delete_config_map_delay(self, framework_id):
        gevent.spawn(self.__delete_config_map_sleep, framework_id)

    def __delete_config_map_sleep(self, framework_id):
        gevent.sleep(K8SAdapter.CONFIG_MAP_DEL_WAIT)
        self.__delete_config_map(framework_id)

    def delete_jobs(self, job_ids, framework_id):
        self.logger.trace("Delete jobs: %s, framework_id=%s" % (job_ids, framework_id))
        for j in job_ids:
            try:
                self.delete_job(j[0])
            except Exception, ex:
                self.logger.warn("Error deleteing job: %s" % ex)
        self.__delete_config_map_delay(framework_id)

    def delete_job(self, job_id):
        k8s_job_id = self.__job_id_2_k8s_job_id(job_id)
        self.logger.debug("Deleting job: %s (%s k8s job)" % (job_id, k8s_job_id))
        body = client.V1DeleteOptions()
        resp = self.batch_v1.delete_namespaced_job(name = k8s_job_id,
                                                  namespace = self.namespace,
                                                  body = body,
                                                  grace_period_seconds = 0)
        self.logger.trace("Delete resp: %s" % resp)

    def get_job_id_tuple(self, job_id):
        # handle task array in the future
        id = (job_id,None,None)
        return id

    def get_job_status(self, job_id):
        k8s_job_id = self.__job_id_2_k8s_job_id(job_id)
        self.logger.debug("Getting status for job: %s (%s k8s job)" % (job_id, k8s_job_id))
        status_resp = self.batch_v1.read_namespaced_job_status(name = k8s_job_id,
                                                               namespace = self.namespace)
        active = status_resp.status.active
        succeeded = status_resp.status.succeeded
        failed = status_resp.status.failed
        self.logger.debug("Job status: active=%s, succeeded=%s, failed=%s" %
                          (active, succeeded, failed))
        self.logger.trace("Job status: %s" % status_resp.status)
        if (active is None or active == 0) and (failed is not None and failed > 0):
            raise UnknownJob("Job %s has no active pods and has failed count of %s" % (job_id, failed))
        # this exception indicates job completion (requires by JobMonitor)
        if succeeded:
            raise CompletedJob("Job %s succeeded" % job_id)
        return status_resp.status

    def get_job_accounting(self, job_id):
        self.logger.debug("Getting accounting for job: %s" % job_id)
        try:
            # fill with dummy element for now in order not to cause requesting it multiple times
            acct = {"k8s_accounting": "dummy"}
        except Exception, ex:
            self.logger.debug("Failed to get accounting for job %s: %s" % (ex, job_id))
        return acct

    def unregister_slave(self, request):
        self.logger.debug("Unregister slave: %s" % request)

    def __job_id_2_k8s_job_id(self, job_id):
        return "-".join(job_id.split("-")[:-1])

# Testing
if __name__ == '__main__':
    adapter = K8SAdapter()
    adapter.set_command()
#    print adapter.get_job_id_tuple("k8sjob")
    jobs_num = 2
    job_ids = adapter.submit_jobs(100, jobs_num, {'URB_FRAMEWORK_ID': 'framework-1'})
    print "Sleeping for 5 seconds"
    gevent.sleep(5)
    for jt in job_ids:
        j = jt[0]
        print "Getting job status for %s" % j
        print adapter.get_job_status(j)
        print "Getting job accounting for %s" % j
        print adapter.get_job_accounting(j)
#        job_id = gevent.spawn(adapter.delete_job, j)
        adapter.delete_job(j)
    print "Sleeping for 5 seconds"
    gevent.sleep(5)
    print "Done"


