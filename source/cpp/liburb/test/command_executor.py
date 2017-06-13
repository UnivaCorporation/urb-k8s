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
import time

# Endpoint constants
base_endpoint = 'urb.endpoint.'
master_endpoint = base_endpoint+ '0'
mesos_channel = master_endpoint + ".mesos"
monitor_channel = 'urb.service.monitor'

command_pids = {}
command_return = {}

tasks = {}

class Unbuffered(object):
   def __init__(self, stream):
       self.stream = stream
   def write(self, data):
       self.stream.write(data)
       self.stream.flush()
   def __getattr__(self, attr):
       return getattr(self.stream, attr)

sys.stdout = Unbuffered(sys.stdout)
sys.sterr = Unbuffered(sys.stderr)

# Handle our child exiting
def sig_handler(signum,frame):
    global command_return
    # Our child exits with sig 9 when all is good... so map that to 0
    pid, ret = os.wait()
    print "Our child", pid, "exited with: ", ret
    for task_id, tpid in command_pids.items():
        if pid == tpid:
            command_return[task_id] = (pid,ret)
            if tasks.has_key(task_id):
                del tasks[task_id]


# Send a register message to our server
def send_register(r,source_channel):
    register= {}
    register["executor_id"] = { 'value' : os.environ['URB_EXECUTOR_ID'] }
    register["framework_id"] = { 'value' : os.environ['URB_FRAMEWORK_ID'] }
    payload = register
    slave_id = os.environ['URB_SLAVE_ID']
    slave_id_channel = slave_id[slave_id.index(":")+1:]
    resp = { 'source_id' : source_channel, 'target':"RegisterExecutorMessage", 'payload_type':"json",
             'payload': { 'mesos.internal.RegisterExecutorMessage' : payload}, 'reply_to':slave_id_channel }
    print "Sending register message: " + str(resp)
    r.lpush(mesos_channel, json.dumps(resp))

# Send a reregister message to our server
def send_reregister(r,source_channel):
    register= {}
    register["executor_id"] = { 'value' : os.environ['URB_EXECUTOR_ID'] }
    register["framework_id"] = { 'value' : os.environ['URB_FRAMEWORK_ID'] }
    register['tasks'] = tasks.values()
    payload = register
    slave_id = os.environ['URB_SLAVE_ID']
    slave_id_channel = slave_id[slave_id.index(":")+1:]
    resp = { 'source_id' : source_channel, 'target':"ReregisterExecutorMessage", 'payload_type':"json",
             'payload': { 'mesos.internal.ReregisterExecutorMessage' : payload}, 'reply_to':slave_id_channel }
    print "Sending reregister message: " + str(resp)
    r.lpush(mesos_channel, json.dumps(resp))

# Send a heartbeat to our server
def send_heartbeat(r,source_channel):
    heartbeat= {}
    heartbeat["channel_info"] = {}
    heartbeat["channel_info"]["channel_id"] = source_channel
    heartbeat["channel_info"]["framework_id"] = os.environ['URB_FRAMEWORK_ID']
    heartbeat["channel_info"]["slave_id"] = os.environ['URB_SLAVE_ID']
    heartbeat["channel_info"]["executor_id"] = os.environ['URB_EXECUTOR_ID']
    payload = heartbeat
    resp = { 'source_id' : source_channel, 'target':"HeartbeatMessage", 'payload_type':"json",
             'payload':  payload } 
    print "Sending hearbeat message: " + str(resp)
    r.lpush(monitor_channel, json.dumps(resp))


# We are done... send update and exit
def status_update(r,source_channel,task_id,status):
    status_update = {}
    status_update['framework_id'] = { 'value' : os.environ['URB_FRAMEWORK_ID'] }
    status_update['status'] = {}
    status_update['timestamp'] = time.time()
    status_update['slave_id'] = {  'value' : os.environ['URB_SLAVE_ID'] }
    status_update['status']['timestamp'] = time.time()
    status_update['status']['slave_id'] = {  'value' : os.environ['URB_SLAVE_ID'] }
    status_update['status']['task_id'] = {'value' : task_id }
    status_update['status']['state']= status
    status_update["executor_id"] = { 'value' : os.environ['URB_EXECUTOR_ID'] }
    status_update['uuid'] = "1234"
    payload = { 'update' : status_update }
    resp = { 'source_id' : source_channel, 'target':"StatusUpdateMessage", 'payload_type':"json",
             'payload': { 'mesos.internal.StatusUpdateMessage' : payload }}
    print "Sending Status Update message: " + str(resp)
    r.lpush(mesos_channel, json.dumps(resp))

# Let them know we are running
def command_running(r,source_channel,task_id):
    status_update(r,source_channel,task_id,"TASK_RUNNING")

# We are done... send update and exit
def command_complete(r,source_channel,task_id):
    status_update(r,source_channel,task_id,"TASK_FINISHED")
    #sys.exit(command_return)

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

    r = redis.StrictRedis(host=hostname, port=port, db=0)
    endpoint_id = r.incr('urb.endpoint.id')
    my_channel = base_endpoint + str(endpoint_id)
    my_channel_notify = my_channel+".notify"
    print "My channel",my_channel

    task_id="unknown"

    # Get our other environment variables
    framework_id = {
        "value":os.environ["URB_FRAMEWORK_ID"]
    }

    # Let the master know we are here
    send_register(r,my_channel)

    last_heartbeat = 0

    # Set up our signal handler
    signal.signal(signal.SIGCHLD, sig_handler)

    # Now wait for an launchTasks
    while True:
        # Lets wait for some register messages
        m = r.brpop(my_channel+".notify",1)
        if m:
            m=m[1]
        # First check if our child is done
        for task_id, ret in command_return.items():
            command_complete(r,my_channel_notify,task_id)
        # Now check if we should send a heartbeat
        if time.time() - last_heartbeat > 60:
            send_heartbeat(r,my_channel_notify)
            last_heartbeat = time.time()
        # No message...
        if m == None:
            continue

        # Common message handling
        urb_message = json.loads(m)
        print urb_message
        print "source id", urb_message['source_id']
        parts = urb_message['source_id'].split('.')
        id = parts[2]
        # Channel global callback
        notify_response_channel = "urb.endpoint." + id + ".notify"
        # Override reply channel if supplied
        response_channel = urb_message.get("reply_to")
        if response_channel == None:
            response_channel = notify_response_channel

        if urb_message['target'] == "RunTaskMessage":
            # All we need to do here is launch an executor....
            # Could be huge
            #print "Received launch tasks message: " + str(urb_message)
            print "Received RunTasks message" + str(urb_message)
            t = urb_message['payload']['task']
            task_id = t['task_id']['value']
            tasks[task_id] = t
            # Launch an executor
            if t.has_key('command'):
                newpid = os.fork()
                if newpid == 0:
                    command_running(r,my_channel,task_id)
                    # Have to run these commands through bash
                    os.execv("/bin/bash",["bash","-c",t['command']['value']])
                else:
                    command_pids[task_id] = newpid
        elif urb_message['target'] == "ServiceDisconnectedMessage":
            print "Received ServiceDisconnected message"
            # Need to reconnect
            send_reregister(r,my_channel)
        elif urb_message['target'] == "KillTaskMessage":
            print "Received KillTask message"
            task_id = urb_message['payload']['task_id']['value']
            command_pid = command_pids.get(task_id,0)
            if command_pid != 0:
                try:
                    os.kill(command_pid, signal.SIGTERM)
                    time.sleep(5)
                    if command_return != -1:
                        command_complete(r,my_channel,task_id)
                    os.kill(command_pid, signal.SIGKILL)
                    sleep(5)
                except Exception, ex:
                    print 'Caught execption killing child', ex
                command_complete(r,my_channel,task_id)
        elif urb_message['target'] == "ShutdownExectuorMessage":
            print "Received ShutdownExectuor message"
            for task_id, command_pid in command_pids.items():
                if command_pid != 0:
                    os.kill(command_pid, signal.SIGTERM)
                    time.sleep(5)
                    if command_return != -1:
                        command_complete(r,my_channel,task_id)
                    os.kill(command_pid, signal.SIGKILL)
                    sleep(5)
                command_complete(r,my_channel,task_id)
            sys.exit(0)

if __name__ == '__main__':
    main()
