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
import subprocess
import pwd
import signal
import time
import json
import distutils.util

from urb.messaging.message_handler import MessageHandler
from urb.messaging.channel_factory import ChannelFactory
from urb.config.config_manager import ConfigManager
from urb.messaging.message import Message
from urb.messaging.mesos.launch_tasks_message import LaunchTasksMessage
from urb.utility.task_tracker import TaskTracker
from urb.utility.executor_tracker import ExecutorTracker
from urb.messaging.service_disconnected_message import ServiceDisconnectedMessage
from urb.messaging.slave_shutdown_message import SlaveShutdownMessage

class ExecutorHandler(MessageHandler):
    # Actual Mesos version has to be set by the build procedure
    MESOS_VERSION = "1.4.0"

    def __init__(self, channelName,executor_runner):
        MessageHandler.__init__(self, channelName)
        cm = ConfigManager.get_instance()
        self.urb_lib_path = cm.get_config_option('ExecutorHandler', 'urb_lib_path')
        self.fetcher_path = cm.get_config_option('ExecutorHandler', 'fetcher_path')
        self.command_executor_path = cm.get_config_option('ExecutorHandler', 'command_executor_path')

        self.ld_library_path = cm.get_config_option('ExecutorHandler', 'ld_library_path')
        self.logger.debug("LD_LIBRARY_PATH from config: %s" % self.ld_library_path)
        # Add platform specific path
        ld_library_path_platform = os.path.join(self.ld_library_path, distutils.util.get_platform())
        self.ld_library_path += ':' + ld_library_path_platform
        self.logger.debug("Adding platform specific LD_LIBRARY_PATH: %s" % self.ld_library_path)
        # Add from the environment
        if "LD_LIBRARY_PATH" in os.environ:
            self.logger.debug("Adding environment LD_LIBRARY_PATH: %s" % os.environ['LD_LIBRARY_PATH'])
            self.ld_library_path += ':' + os.environ['LD_LIBRARY_PATH']
        self.logger.debug("LD_LIBRARY_PATH: %s" % self.ld_library_path)

        self.executor_runner = executor_runner
        self.executor_pids = []
        self.executor_rets = []
        self.shutdown = False

    def get_target_executor(self, target):
        supported_target_dict = {
            LaunchTasksMessage.target() : self.launch_tasks,
            ServiceDisconnectedMessage.target() : self.service_disconnected,
            SlaveShutdownMessage.target() : self.slave_shutdown,
        }
        return supported_target_dict.get(target)

    def __build_command_executor(self,task_id,command_info):
        command_executor =  {}
        command_executor['executor_id'] = task_id
        command_executor['framework_id'] = self.executor_runner.framework_id
        command_executor['name'] = "(Task " + task_id['value'] + ") "
        command_executor['source'] = task_id['value']
        command_executor['command'] = command_info
        command_executor['command']['value'] = self.command_executor_path
        return command_executor

    def __fetch_uris(self,uris,user):
        action = 'BYPASS_CACHE' # 0 - BYPASS_CACHE, 1 - DOWNLOAD_AND_CACHE, 2 - RETRIEVE_FROM_CACHE
        items = []
        for u in uris:
            value = u['value']
            if u.has_key('executable'):
                executable = True
            else:
                executable = False
            extract = True
            if u.has_key('extract'):
                extract = u['extract']
            uri = {'value' : value, 'executable' : executable, 'extract' : extract, 'cache' : False}
            item = {'uri' : uri, 'action' : action}
            items.append(item)

        fetcher_info = {'sandbox_directory' : self.executor_runner.mesos_work_dir,
                        'work_directory' : self.executor_runner.mesos_work_dir,
                        'user' : user,
                        'items' : items,
                        'frameworks_home' : self.executor_runner.mesos_work_dir}

        fetcher_info_env = "MESOS_FETCHER_INFO='" + json.dumps(fetcher_info) + "'"

        # Build environment
        fetch_env = [
            fetcher_info_env,
            'LD_LIBRARY_PATH='+self.ld_library_path,
            'GLOG_log_dir="'+self.executor_runner.mesos_work_dir+'"',
        ]

        # Now run the fetch
        cmd = "/usr/bin/env " + " ".join(fetch_env) + " " + self.fetcher_path
        self.logger.debug("Calling fetcher:  %s" % cmd)
        os.system(cmd)

    def __sig_child_handler(self, signum, frame):
        # Our child exits with sig 9 when all is good... so map that to 0
        ret = 0
        pid = None
        try:
            status = None
            sig = None
            core = False
            self.logger.debug("Running children: %s" % self.executor_pids)
            self.logger.debug("Got signal %s" % signum)
            pid, ret = os.wait()
            self.logger.debug("After wait")
            msg = "Child %s: wait returned code %s which means:" % (pid, ret)
            if os.WIFSIGNALED(ret):
                sig = os.WTERMSIG(ret)
                msg += " signalled %s" % sig
            if os.WIFEXITED(ret):
                status = os.WEXITSTATUS(ret)
                msg += " exited %s" % status
            if os.WIFSTOPPED(ret):
                msg += " stopped %s" % os.WSTOPSIG(ret)
            if os.WCOREDUMP(ret):
                core = True
                msg += " core dumped"
            if os.WIFCONTINUED(ret):
                msg += " contunied"

            self.logger.debug(msg)

            if pid in self.executor_pids:
                self.executor_pids.remove(pid)
                self.executor_rets.append((status, sig, core))
            else:
                self.logger.error("Pid %s is not a child" % pid)

            # sometimes signal handler is not called, clean here zombies
            for pid in self.executor_pids:
                p, r = os.waitpid(pid, os.WNOHANG)
                if p != 0:
                    self.logger.debug("Zombie with pid %d found, exit code=%d" % (p, r))
                    self.executor_pids.remove(pid)
                    #self.executor_rets.append((status, sig, core))

            ret = 0
            if len(self.executor_pids) == 0:
                self.logger.trace("Statuses of all executors: %s" % self.executor_rets)
                for st, sg, co in self.executor_rets:
                    if st is not None and st != 0:
                        ret = st
                    if co:
                        ret = 1
                self.logger.info("Exit with code %s" % ret)
                sys.exit(ret)

        except Exception, ex:
            self.logger.error("Error waiting for child process: %s" % ex)
            if len(self.executor_pids) <= 1:
                self.logger.warn("No more child processes, exit with success: pids=%s, last pid=%s, ret=%s" % (self.executor_pids, pid, ret))
                sys.exit(0)
            else:
                self.logger.info("Children left: %s" % self.executor_pids)

    def service_disconnected(self, request):
        tasks = [ v for k,v in TaskTracker.get_instance() ]
        self.logger.debug("Service disconnected, register executor runner. Send task data back to service: %s" % tasks)
        if len(tasks) > 0:
            self.executor_runner.register_executor_runner(tasks)
        else:
            self.executor_runner.register_executor_runner()
        return None, None

    def slave_shutdown(self, request):
        self.logger.debug('Slave shutdown received, exiting')
        self.shutdown = True
        #time.sleep(2)
        sys.exit(0)

    def launch_tasks(self, request):
        # Could be huge
        self.logger.trace("Received launch tasks message: " + str(request))
        payload = request.get('payload')
        message = payload['mesos.internal.LaunchTasksMessage']
        if not message.has_key('tasks'):
            self.logger.debug("No tasks to launch. Shutting down.")
            # Shutdown... no work...
            self.shutdown = True
            #time.sleep(2)
            sys.exit(0)
            return
        for t in message['tasks']:
            task_id = t['task_id']
            self.logger.debug('Launching task: %s' % task_id['value'])
            TaskTracker.get_instance().add(task_id['value'], t)
            # Launch an executor
            e = None
            task_command = t.get('command') 
            if task_command:
                # Make a fake executor for launching this command
                e = self.__build_command_executor(task_id,task_command)
            else:
                # We can use the one that was passed
                e =  t['executor']
            executor_id = e['executor_id']
            executor_id_value = executor_id['value']
            # make unique executor id (so in case of executor http api on subscribe we can find corresponding slave)
#            executor_id_value_unique = executor_id_value + "_%s" % t['task_id']['value']
            executor_id_value_unique = executor_id_value
            executor_tracker = ExecutorTracker.get_instance()
            executor = executor_tracker.get(executor_id_value)
            if executor is not None:
                self.logger.debug('Executor %s is already running'  % executor_id_value)
                return None, None

            executor_command = e.get('command')
            if executor_command is None:
                self.logger.warn('No command provided for executor %s' % executor_id_value)
                return None, None

            # First allocate the executor
            executor = {
                'executor_id' : executor_id,
                'framework_id' : self.executor_runner.framework_id,
                'command' : executor_command,
            }
            if e.has_key('data'):
                executor['data'] = e['data']
            executor_tracker.add(executor_id_value, executor)

            # Fetch URIs if necessary
            user = pwd.getpwuid(os.getuid())[0]
            if executor_command.has_key('uris'):
                self.__fetch_uris(e['command']['uris'],user)

            self.logger.debug('Launching executor: ' + executor_command['value'])

            # get environment variables which may come with UGE -v ot -V flags
            # as well as from user's .urb_executor_env file
            exec_env = os.environ
            # remove unnecessary ones
            for dele in ["_", "SHLVL", "PWD", "LS_COLORS"]:
                if dele in exec_env:
                    del exec_env[dele]

            if "URB_MASTER" not in exec_env:
                self.logger.error("Executor environment missing URB_MASTER environment variable")
            if "PATH" not in exec_env:
                self.logger.warn("Executor environment missing PATH environment variable")

            exec_env["URB_SLAVE_ID"] = self.executor_runner.slave_id['value']
            exec_env["URB_FRAMEWORK_ID"] = self.executor_runner.framework_id['value']
            exec_env["URB_EXECUTOR_ID"] = executor_id_value_unique
            exec_env["MESOS_NATIVE_LIBRARY"] = self.urb_lib_path # will be deprecated in future mesos releases
            exec_env["MESOS_NATIVE_JAVA_LIBRARY"] = self.urb_lib_path
            exec_env["MESOS_DIRECTORY"] = self.executor_runner.mesos_work_dir

            # for http api
            exec_env["MESOS_FRAMEWORK_ID"] = exec_env["URB_FRAMEWORK_ID"]
            exec_env["MESOS_EXECUTOR_ID"] = exec_env["URB_EXECUTOR_ID"]
            if "MESOS_AGENT_ENDPOINT" in exec_env:
                exec_env["MESOS_SLAVE_PID"] = "@" + exec_env["MESOS_AGENT_ENDPOINT"]
            if "MESOS_EXECUTOR_SHUTDOWN_GRACE_PERIOD" not in exec_env:
                exec_env["MESOS_EXECUTOR_SHUTDOWN_GRACE_PERIOD"] = "60secs"

            if "LD_LIBRARY_PATH" in exec_env and exec_env["LD_LIBRARY_PATH"] != self.ld_library_path:
                self.logger.debug("Custom LD_LIBRARY_PATH provided: %s, appending default one from the global executor config: %s" % \
                                  (exec_env["LD_LIBRARY_PATH"], self.ld_library_path))
                exec_env["LD_LIBRARY_PATH"] = exec_env["LD_LIBRARY_PATH"] + ":" + self.ld_library_path
            else:
                exec_env["LD_LIBRARY_PATH"] = self.ld_library_path

            if "USER" in exec_env and exec_env["USER"] != user:
                self.logger.warn("Executor environment: mismatch in USER environment variable and actual user: %s %s" % \
                                 (exec_env["USER"], user))
            exec_env["USER"] = user

            if "GLOG_log_dir" not in exec_env:
                exec_env["GLOG_log_dir"] = self.executor_runner.mesos_work_dir

            if executor_command.has_key('environment'):
                for v in executor_command['environment']['variables']:
                    if v['name'] in exec_env and v['value'] != exec_env[v['name']]:
                        self.logger.warn("Executor environment valuable %s=%s is already present, overriding with: %s from executor command" % \
                                         (v['name'], exec_env[v['name']], v['value']))
                    exec_env[v['name']] = v['value']

# disabled to source executor profile on upper level (in bin/urb-executor-runner) to support "environment modules" mechanism
#            self.logger.trace("Current executor env: %s" % exec_env)
#
#            # source user environment file
#            user_env = {}
#            user_env_file = os.path.join(os.path.expanduser('~'), '.urb.executor_profile')
#            self.logger.debug("User executor environment file: %s" % user_env_file)
#            if os.path.isfile(user_env_file):
#                if "URB_FRAMEWORK_NAME" in exec_env:
#                    user_env = self.__get_user_env(user_env_file, "URB_FRAMEWORK_NAME", exec_env["URB_FRAMEWORK_NAME"])
#                else:
#                    self.logger.warn("URB_FRAMEWORK_NAME is not in executor environment")
#            else:
#                self.logger.debug("No user executor environemnt file found: %s" % user_env_file)
#
#            # add env variables sourced from user env file
#            if user_env:
#                for k in user_env:
#                    if k in ["PATH", "LD_LIBRARY_PATH"]:
#                        self.logger.debug('Changed current env var: %s=%s' % (k, exec_env[k]))
#                        user_paths = user_env[k].split(':')
#                        curr_paths = exec_env[k].split(':')
#                        added_paths = [path for path in user_paths if path not in curr_paths]
#                        added_path_str = ':'.join(added_paths)
#                        exec_env[k] = added_path_str + ":" + exec_env[k]
#                        self.logger.debug('Prepending %s with %s: %s' % (k, added_path_str, exec_env[k]))
#                    elif k in exec_env:
#                        self.logger.debug('Owerriding existing env var %s=%s with user value: %s' % (k, exec_env[k], user_env[k]))
#                    else:
#                        self.logger.debug('Adding new user env var: %s=%s' % (k, user_env[k]))
#                        exec_env[k] = user_env[k]

            self.logger.debug('Complete executor environment: %s' % exec_env)
            signal.signal(signal.SIGCHLD, self.__sig_child_handler)
            newpid = os.fork()
            if newpid == 0:
                signal.signal(signal.SIGCHLD, signal.SIG_DFL)
                os.chdir(self.executor_runner.mesos_work_dir)
                # Have to run these commands through bash
                os.execve("/bin/bash",["executor","-c",executor_command['value']],exec_env)
            else:
                self.logger.debug('Launched task %s with pid: %s' % (task_id['value'], newpid))
                self.executor_pids.append(newpid)
                self.logger.debug('All child processes: %s' % self.executor_pids)
        return None, None

    def __get_user_env(self, user_env_file, env_var_name, env_var_value):
        ignore = ['_', 'SHLVL', 'PWD']
        cmd = "env -i bash".split()
        input = '%s=%s . "%s"; /bin/env' % (env_var_name, env_var_value, user_env_file)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_data, stderr_data = p.communicate(input=input)
        if stderr_data:
            self.logger.error('Error in getting env vars from user environment file %s: %s' % (user_env_file, stderr_data))
            return None
        else:
            lines = stdout_data.splitlines()
            self.logger.trace("New env: %s" % lines)
            sourced_env = dict(item.split('=') for item in lines if '=' in item)
            new_env = dict((k,v) for k,v in sourced_env.items() if k not in ignore)
            self.logger.debug("Environment sourced from user's script: %s" % new_env)
            return new_env

# Testing
if __name__ == '__main__':
    pass
