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
from urb.utility.utils import isfloat

import gevent
import uuid
import os
import copy
import re
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import yaml


class K8SAdapter(object):
    """ Kubernetes Adapter class. """

    URB_EXECUTOR_RUNNER = "urb-executor-runner"
    JOB_NAME_MAX_SIZE = 63
    UUID_SIZE = 8

    def __init__(self, k8s_registry_path = ""):
        self.logger = LogManager.get_instance().get_logger(
            self.__class__.__name__)
        self.logger.info("K8s registry path: %s" % k8s_registry_path)
        self.configure()
        self.channel_name = None

        with open(os.path.join(os.path.dirname(__file__), K8SAdapter.URB_EXECUTOR_RUNNER + ".yaml")) as fj:
            self.job = yaml.load(fj)
            if len(k8s_registry_path) != 0:
                self.job['spec']['template']['spec']['containers'][0]['image'] = k8s_registry_path + "/" + K8SAdapter.URB_EXECUTOR_RUNNER

            # URB_MASTER environment variable has to be set in urb-master.yaml
            urb_master = os.environ.get('URB_MASTER')
            if not urb_master:
                self.logger.error("URB_MASTER is not set in urb-master.yaml")
            urb_master_env = {'name' : 'URB_MASTER',
                              'value' : urb_master }
            self.job['spec']['template']['spec']['containers'][0]['env'].append(urb_master_env)

            self.logger.debug("Loaded job yaml template: %s" % self.job)
            # uuid.time_low size is 8, plus 2 dashes ('-')
            self.job_name_template_size = len(self.job['metadata']['name']) + K8SAdapter.UUID_SIZE + 2
            if self.job_name_template_size >= K8SAdapter.JOB_NAME_MAX_SIZE:
                self.logger.error("Job name template %s is too long, should be < %s bytes" %
                                  (self.job_name_template_size, K8SAdapter.JOB_NAME_MAX_SIZE))
            self.image = self.job['spec']['template']['spec']['containers'][0]['image']

        self.core_v1 = client.CoreV1Api()
        self.batch_v1 = client.BatchV1Api()

    def configure(self):
        # all jobs inherit URB master namespace passed via environment variable
        self.namespace = os.environ.get('URB_NAMESPACE', 'default')
        self.logger.info("K8s namespace: %s" % self.namespace)

        self.cm = ConfigManager.get_instance()
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
            os.environ['KUBERNETES_SERVICE_HOST'] = 'kubernetes.default'
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
        # after specified time since job submission
        return (True, 2)

    def register_executor_runner(self, framework_id, slave_id, *args, **kwargs):
        self.logger.trace(
            "Register executor runner for framework id %s, slave id %s" %
            (framework_id, slave_id))

    def register_framework(self, max_tasks, concurrent_tasks, framework_env, user=None, *args, **kwargs):
        job_ids = self.submit_jobs(max_tasks, concurrent_tasks, framework_env, user, *args, **kwargs)
        return job_ids

    def __retrieve_pod_name(self, label_selector):
        pod_name = None
        list_resp = self.core_v1.list_namespaced_pod(namespace = self.namespace,
                                                     label_selector = label_selector)
        self.logger.trace("list_resp: %s" % list_resp)
        items = len(list_resp.items)
        if items > 1:
            self.logger.warn("Only one element expected in pod list for label selector: %s" % label_selector)
        elif items == 0:
            self.logger.warn("No elements in pod list for label selector: %s" % label_selector)
        else:
            pod_name = list_resp.items[0].metadata.name
        return pod_name

    def __get_job_ids(self, label_selectors):
        retry_label_selectors = []
        job_ids = []
        for label_selector in label_selectors:
            pod_name = self.__retrieve_pod_name(label_selector)
            if not pod_name:
                retry_label_selectors.append(label_selector)
                continue
            # job id is set as pod name as it can be exposed as JOB_ID environment variable mapped from
            # metadata.name to executor runner
            job_id = (pod_name,None,None)
            self.logger.info("Got pod id: %s for label selector %s" % (pod_name, label_selector))
            job_ids.append(job_id)
        return (job_ids, retry_label_selectors)

    def scrub_framework_name(self, framework_name):
        scrubbed_framework_name = re.sub('[\s|(|)|(:)|(,)|(.)|(^)|($)|(+)|(?)|(\{)|(\})|(\[)|(\])|(\\)|(\()|(\))]+', '',
            framework_name)
        return scrubbed_framework_name

    def __append_job_name(self, job_name, append, concurrent_tasks):
        # do not exceed name limit of 63 bytes
        jn = job_name
        append = re.sub('[\s|(|)|(:)|(,)|(.)|(^)|($)|(+)|(?)|(\{)|(\})|(\[)|(\])|(\\)|(\()|(\))]+', '', append)
        append = append.lower()
        left = K8SAdapter.JOB_NAME_MAX_SIZE - self.job_name_template_size - len(job_name)
        if concurrent_tasks > 1:
            l = len(str(concurrent_tasks)) + 1
            left -= l
        if len(append) > left:
            jn += "-%s" % append[:left]
        else:
            jn += "-%s" % append
        return jn

    def __from_tasks(self, i, job_name, tasks, concurrent_tasks, resource_mapping):
        req_key = None
        tasks_len = len(tasks) if tasks else 0
        jn = job_name
        if tasks_len > 0:
            indx = i if i < tasks_len else tasks_len - 1
            task = tasks[indx]
            self.logger.trace("task index: %d" % indx)
            # create requests
            resources = task.get('resources')
            self.logger.trace("resource_mapping=%s" % resource_mapping)
            if resources is not None and len(resource_mapping) > 0 and resource_mapping != 'none' and resource_mapping != 'false':
                requests = {}
                for rm in resource_mapping.split(";"):
                    rm = rm.strip()
                    for resource in resources:
                        if resource['name'] == "mem":
                            if rm == "mem" or rm == "true":
                                requests['memory'] = str(resource['scalar']['value']) + "M"
                            elif "mem" == rm[0:3]:
                                mul = self.__scale_resource(rm)
                                requests['memory'] = str(int(resource['scalar']['value'])*mul) + "M"
                        elif resource['name'] == "cpus":
                            if rm == "cpu" or rm == "true":
                                requests['cpu'] = str(int(resource['scalar']['value']))
                            elif "cpu" == rm[0:3]:
                                mul = self.__scale_resource(rm)
                                requests['cpu'] = str(int(resource['scalar']['value'])*mul)

                if len(requests) > 0:
                    self.logger.info("Requests: %s" % requests)
                    req_key = {'requests' : requests }
            task_name = task.get('name')
            if task_name:
                jn = self.__append_job_name(job_name, task_name, concurrent_tasks)
            else:
                task_id = task.get('task_id')
                if task_id:
                    jn = self.__append_job_name(job_name, task_id['value'], concurrent_tasks)
            if concurrent_tasks > 1:
                jn += "-%d" % i
        elif concurrent_tasks > 1:
            jn = "%s-%d" % (job_name, i)
        return (jn, req_key)

    def submit_jobs(self, max_tasks, concurrent_tasks, framework_env, user=None, *args, **kwargs):
        self.logger.info("submit_jobs: max_tasks=%s, concurrent_tasks=%s, framework_env=%s, user=%s, args=%s, kwargs=%s" %
                         (max_tasks, concurrent_tasks, framework_env, user, args, kwargs))
        job = copy.deepcopy(self.job)
        framework_name = framework_env['URB_FRAMEWORK_NAME'].lower()
        job_name = self.__append_job_name(self.job['metadata']['name'], framework_name, concurrent_tasks)

        framework_id_env = {'name' : 'URB_FRAMEWORK_ID',
                            'value' : framework_env['URB_FRAMEWORK_ID'] }
        job['spec']['template']['spec']['containers'][0]['env'].append(framework_id_env)

        executor_runner = kwargs.get('executor_runner')
        if executor_runner and len(executor_runner) > 0:
            job['spec']['template']['spec']['containers'][0]['image'] = executor_runner
        else:
            job['spec']['template']['spec']['containers'][0]['image'] = self.image

        self.logger.debug("Executor runner image: %s" %
                           job['spec']['template']['spec']['containers'][0]['image'])

        persistent_volume_claims = kwargs.get('persistent_volume_claims')
        if persistent_volume_claims and len(persistent_volume_claims) > 0:
            for pv in persistent_volume_claims.split(";"):
                pv = pv.strip()
                lst = pv.split(":")
                if len(lst) != 2:
                    self.logger.error("Incorrect format for persistent volume claim: %s, lst=%s" % (pv, lst))
                    continue
                pvc = lst[0]
                path = lst[1]
                self.__add_pv(job, pvc, path)

        tasks = kwargs.get('tasks')
        resource_mapping = str(kwargs.get('resource_mapping')).lower()

        # do two loops to allow more time for controller-uid to be generated
        label_selectors = []
        # should have enough space for uuid part of the name
        uid_suff = uuid.uuid1().hex[:K8SAdapter.UUID_SIZE]
        for i in range(0,concurrent_tasks):
            if i >= max_tasks:
                break
            (jn, req_key) = self.__from_tasks(i, job_name, tasks, concurrent_tasks, resource_mapping)
            if req_key:
                job['spec']['template']['spec']['containers'][0]['resources'] = req_key
            self.logger.trace("Container: %s" % job['spec']['template']['spec']['containers'][0])
            job['metadata']['name'] = "%s-%s" % (jn, uid_suff)
            self.logger.info("Submit k8s job %s in namespace %s" % (job['metadata']['name'], self.namespace))
            self.logger.trace("job body=%s" % job)
            job_resp = self.batch_v1.create_namespaced_job(body = job, namespace = self.namespace)
            self.logger.trace("job_resp: %s" % job_resp)
            uid = job_resp.metadata.uid
            label_selector = "controller-uid=" + uid
            label_selectors.append(label_selector)

        (job_ids, retry_label_selectors) = self.__get_job_ids(label_selectors)
        if len(retry_label_selectors) > 0:
            self.logger.warn("Could not get pod names for following: %s" % retry_label_selectors)
            gevent.sleep(1)
            (jids, retry_ls) = self.__get_job_ids(retry_label_selectors)
            job_ids.extend(jids)
            if len(retry_ls) > 0:
                self.logger.error("After delay, could not get pod names for following: %s" % retry_label_selectors)

        return job_ids

    def __scale_resource(self, resource):
        mul = 1.
        pos = resource.find('*', 3)
        v = resource[pos+1:]
        if pos != -1 and isfloat(v):
            mul = float(v)
        else:
            pos = resource.find('/', 3)
            v = resource[pos+1:]
            if pos != -1 and isfloat(v):
                mul = 1./float(resource[pos+1:])
        return mul

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

    def delete_jobs(self, job_ids, framework_id):
        self.logger.trace("Delete jobs: %s, framework_id=%s" % (job_ids, framework_id))
        for j in job_ids:
            try:
                self.delete_job(j[0])
            except Exception, ex:
                self.logger.warn("Error deleteing job: %s" % ex)

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
        job_status_resp = self.batch_v1.read_namespaced_job_status(name = k8s_job_id,
                                                               namespace = self.namespace)
        active = job_status_resp.status.active
        succeeded = job_status_resp.status.succeeded
        failed = job_status_resp.status.failed
        self.logger.debug("Job status: active=%s, succeeded=%s, failed=%s" %
                          (active, succeeded, failed))
        self.logger.trace("Job status: %s" % job_status_resp.status)
        if (active is None or active == 0) and (failed is not None and failed > 0):
            # will trigger task lost
            raise UnknownJob("Job %s has no active pods and has failed count of %s" % (job_id, failed))
        # this exception indicates job completion (requires by JobMonitor)
        if succeeded:
            raise CompletedJob("Job %s succeeded" % job_id)
        else:
            self.logger.debug("Getting status for pod: %s" % job_id)
            pod_status_resp = self.core_v1.read_namespaced_pod_status(name = job_id,
                                                               namespace = self.namespace)
            status = pod_status_resp.status
            self.logger.trace("Pod status: %s" % status)
            phase = status.phase
            if phase in ["Unknown", "Failed"]:
                raise UnknownJob("Pod %s in '%s' phase" % (job_id, phase))
            elif phase == "Pending":
                if hasattr(status, 'conditions') and len(status.conditions) > 0:
                    last_condition = status.conditions[-1]
                    if last_condition.status == "False" and last_condition.type == "PodScheduled":
                        self.logger.debug("Pod %s has last condition: status=%s, type=%s, reason=%s, message=%s" %
                                          (job_id, last_condition.status, last_condition.type,
                                           last_condition.reason, last_condition.message))
            elif phase == "Running":
                #status.reason
                if hasattr(status, 'container_statuses'):
                    container_status = status.container_statuses[0]
                    #container_status.ready
                    if hasattr(container_status, 'state'):
                        state = container_status.state
                        if hasattr(state, 'running') and state.running:
                            self.logger.debug("Pod status: running")
                        elif hasattr(state, 'terminated') and state.terminated:
                            terminated = state.terminated
                            self.logger.debug("Pod status: terminated")
                            if hasattr(terminated, 'reason'):
                                if terminated.reason == "Completed":
                                    raise CompletedJob("Pod %s terminated with reason: %s" % (job_id, terminated.reason))
                                else:
                                    raise UnknownJob("Pod %s is in terminated state with exit code: %s" %
                                                    (job_id, terminated.exit_code if hasattr(terminated, 'exit_code') else "unknown"))
                            else:
                                self.logger.warn("Pod status: terminated: no reason field")
                        elif hasattr(state, 'waiting') and state.waiting:
                            self.logger.debug("Pod status: waiting")
                            warn = True
                            waiting = state.waiting
                            if hasattr(waiting, 'reason') and waiting.reason:
                                warn = False
                                self.logger.debug("Pod status: waiting: reason=%s" % waiting.reason)
                                if waiting.reason in ["ImagePullBackOff", "ImageInspectError", "ErrImagePull",
                                                    "ErrImageNeverPull", "RegistryUnavailable", "InvalidImageName"]:
                                    raise UnknownJob("Pod %s is in waiting state due to %s reason" %
                                                    (job_id, waiting.reason))
                            if hasattr(waiting, 'message') and waiting.message:
                                warn = False
                                self.logger.debug("Pod status: waiting: message=%s" % waiting.message)
                                if any(m in waiting.message for m in ["not found", "fail", "can't"]):
                                    raise UnknownJob("Pod %s is in waiting state with 'message': %s" %
                                                    (job_id, waiting.message))
                            if warn:
                                self.logger.warn("Pod status: waiting: no details")
                        else:
                            self.logger.error("Pod status: incorrect state")
                    else:
                        self.logger.warn("Pod status: no container state")
                else:
                    self.logger.error("Pod status: no container statuses")

        return job_status_resp.status

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

    def config_update(self):
        self.logger.info("Configuration update")

    def __add_pv(self, job, pvc, path):
        pvc_name = pvc + "-storage"
        volume = {'name' : pvc_name,
                  'persistentVolumeClaim' :
                     { 'claimName' : pvc }
                 }
        volume_mount = {'mountPath' : path,
                        'name' : pvc_name }

        spec = job['spec']['template']['spec']
        if not spec.get('volumes'):
            spec['volumes'] = []
        spec['volumes'].append(volume)

        containers0 = job['spec']['template']['spec']['containers'][0]
        if not containers0.get('volumeMounts'):
            containers0['volumeMounts'] = []
        containers0['volumeMounts'].append(volume_mount)


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


