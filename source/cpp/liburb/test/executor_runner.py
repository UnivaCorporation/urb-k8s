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


import os
import sys
import redis
import json
import subprocess
import signal
import pwd

# Endpoint constants
base_endpoint = 'urb.endpoint.'
master_endpoint = base_endpoint+ '0'
mesos_channel = master_endpoint + ".mesos"

# Executors
executors = {}
executor_pid = None

# Tasks
tasks = {}

# Paths (Just for vagrant box)
urb_lib_path=os.environ.get("URB_LIB_PATH")
urb_lib_file="liburb-0.0.1.so"
fetcher="fetcher"
command_executor="command_executor.py"
urb_build_path=urb_lib_path
urb_lib="/".join([urb_build_path,urb_lib_file])
fetcher_path="/".join([urb_build_path,fetcher])
command_executor_path="/".join([urb_lib_path,"..","test",command_executor])

mesos_work_dir = os.environ.get('TMP',"") + "/urb"

def fetch_uris(uris,user):
    exec_uris = []
    for u in uris:
        # Default is extract
        should_extract = True
        if u.has_key('extract'):
            should_extract = u['extract']
        exec_uri = u['value'] + "+"
        if u.has_key('executable'):
            exec_uri += "1"
        else:
            exec_uri += "0"
        if should_extract:
            exec_uri += "X"
        else:
            exec_uri += "N"
        exec_uris.append(exec_uri)

    # Build environment
    fetch_env = [
        'MESOS_EXECUTOR_URIS="'+" ".join(exec_uris) +'"',
        'MESOS_WORK_DIRECTORY="'+mesos_work_dir+'"',
        'MESOS_USER='+user,
    ]
    # Now run the fetch
    cmd = "/usr/bin/env " + " ".join(fetch_env) + " " + fetcher_path
    print cmd
    os.system(cmd)


# Handle our child exiting
def sig_handler(signum,frame):
    # Our child exits with sig 9 when all is good... so map that to 0
    ret = os.wait()[1]
    if ret == 9:
        ret = 0
    sys.exit(ret)

# Send a hello message to our server
def send_hello(r,source_channel,framework_id,slave_id):
    hello = {}
    hello["slave_id"] = slave_id
    #hello["executor_id"] = executor_id
    hello["framework_id"] = framework_id
    payload = hello
    resp = { 'source_id' : source_channel, 'target':"HelloMessage", 'payload_type':"json",
             'payload': payload }
    print "Sending hello message: " + str(resp)
    r.lpush(mesos_channel, json.dumps(resp))

# Marse the URB_MASTER environment variable to get our connection info
def get_hostname_port():
    urb_scheme = "urb://"
    urb_url = os.environ.get("URB_MASTER")
    if not urb_url:
        print >> sys.stderr, "The URB_MASTER environment variable is required"
        sys.exit(1)
    if not urb_url.startswith(urb_scheme):
        print >> sys.stderr, "The URB_MASTER url must start with",urb_scheme
        print >> sys.stderr, "\tURB_MASTER=%s"%urb_url
        sys.exit(1)

    # Naive urb url parsing...
    port = 6379
    hostname = urb_url[len(urb_scheme):]
    i = hostname.find(":")
    if i != -1:
        port = int(hostname[i+1:])
        hostname = hostname[:i]

    return (hostname,port)


# Main logic
def main():
    # Get our redis server hostname and port
    hostname,port = get_hostname_port()
    print "URB Server Hostname",hostname
    print "URB Server Port", port

    # Create our working directory
    if not os.path.exists(mesos_work_dir):
        os.mkdir(mesos_work_dir)

    r = redis.StrictRedis(host=hostname, port=port, db=0)
    endpoint_id = r.incr('urb.endpoint.id')
    my_channel = base_endpoint + str(endpoint_id)
    print "My channel",my_channel

    # Get our other environment variables
    framework_id = {
        "value":os.environ["URB_FRAMEWORK_ID"]
    }

    # Build our slave info object
    slave_id = {
        "value":"slave-"+os.environ["JOB_ID"]+"."+os.environ["SGE_TASK_ID"]+":"+my_channel+".notify"
    }
    slave_info = {
        'hostname' : r.connection_pool.connection_kwargs['host'],
        'port' : r.connection_pool.connection_kwargs['port'],
        'id' : slave_id
    }
    # The master will fix this up...
    dummy_framework_info = {
        'name':'default',
        'user':'default',
    }

    # Let the master know we are here
    send_hello(r,my_channel,framework_id,slave_id)

    # Now wait for an launchTasks
    while True:
        # Lets wait for some register messages
        m = r.brpop(my_channel+".notify",1)
        if m:
            m=m[1]
        # No message...
        if m == None:
            continue

        # Common message handling
        urb_message = json.loads(m)
        print "source id", urb_message['source_id']
        base1, base2, id = urb_message['source_id'].split('.')
        # Channel global callback
        notify_response_channel = "urb.endpoint." + id + ".notify"
        # Override reply channel if supplied
        response_channel = urb_message.get("reply_to")
        if response_channel == None:
            response_channel = notify_response_channel

        if urb_message['target'] == "RegisterExecutorMessage":
            # We need to handle this message because we are the only ones
            # That know the slave info
            print "Received Registered Executor message: " + str(urb_message)
            m = urb_message['payload']['mesos.internal.RegisterExecutorMessage']
            executor_key = m['executor_id']['value']

            executor_registered = {
              'executor_info' : executors[executor_key],
              'framework_id' : { 'value': m['framework_id']['value'] },
              'framework_info' : dummy_framework_info,
              'slave_id' : slave_id,
              'slave_info' : slave_info,
            }

            payload =  { 'mesos.internal.ExecutorRegisteredMessage' : executor_registered }
            resp = { 'source_id' : my_channel, 'target':"ExecutorRegisteredMessage", 'payload_type':"json",
                 'payload': payload }
            print "Sending ExecutorRegistered message: " + str(resp)
            # always goes to mesos channel
            r.lpush(mesos_channel, json.dumps(resp))

        elif urb_message['target'] == "LaunchTasksMessage":
            # All we need to do here is launch an executor....
            # Could be huge
            #print "Received launch tasks message: " + str(urb_message)
            print "Received launch tasks message"
            if not urb_message['payload']['mesos.internal.LaunchTasksMessage'].has_key('tasks'):
                print "No tasks to launch"
                continue
            for t in urb_message['payload']['mesos.internal.LaunchTasksMessage']['tasks']:
                tasks[t['task_id']['value']] = t
                # Launch an executor
                e = {}
                orig_command = ""
                if t.has_key('command'):
                    # Make a fake executor for launching this command
                    e['executor_id'] = t['task_id']
                    e['framework_id'] = framework_id
                    e['name'] = "(Task " + t['task_id']['value'] + ") "
                    e['source'] = t['task_id']['value']
                    e['command'] = t['command']
                    orig_command = t['command']['value']
                    e['command']['value'] = command_executor_path
                else:
                    e =  t['executor']
                executor_key = e['executor_id']['value']
                if e['command'] and not executors.has_key(executor_key):
                    # First allocate the executor
                    executors[executor_key] = {
                      'executor_id' : e['executor_id'],
                      'framework_id' : framework_id,
                      'command' : e['command'],
                    }
                    if e.has_key('data'):
                        executors[executor_key]['data'] = e['data']

                    # Fetch URIs if necessary
                    if e['command'].has_key('uris'):
                        fetch_uris(e['command']['uris'],pwd.getpwuid(os.getuid())[0])

                    print "Launching executor: " + e['command']['value']
                    exec_env = {
                        "URB_MASTER" : os.environ['URB_MASTER'],
                        "URB_SLAVE_ID" : slave_id['value'],
                        "URB_FRAMEWORK_ID" : framework_id['value'],
                        "URB_EXECUTOR_ID" : e['executor_id']['value'],
                        "MESOS_NATIVE_LIBRARY" : urb_lib, # will be deprecated in the future mesos releases
                        "MESOS_NATIVE_JAVA_LIBRARY" : urb_lib,
                        "LD_LIBRARY_PATH" : urb_lib_path
                    }
                    if e['command'].has_key('environment'):
                        for v in e['command']['environment']['variables']:
                            exec_env[v['name']] = v['value']
                    signal.signal(signal.SIGCHLD, sig_handler)
                    newpid = os.fork()
                    if newpid == 0:
                        os.chdir(mesos_work_dir)
                        # Have to run these commands through bash
                        os.execve("/bin/bash",["executor","-c",e['command']['value']],exec_env)
                    else:
                        executor_pid = newpid

if __name__ == '__main__':
    main()
