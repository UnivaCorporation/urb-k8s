/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include <signal.h>
#include <stdio.h>
#include <ctime>   // localtime
#include <sys/wait.h>

#include <iostream>
#include <list>
#include <string>
#include <sstream>

#include <mesos/executor.hpp>

#include <stout/duration.hpp>
#include <stout/lambda.hpp>
#include <stout/os.hpp>
#include <stout/strings.hpp>

//#include "glog/logging.h"
#include "timer.hpp"

using std::cout;
using std::cerr;
using std::endl;
using std::string;

static pid_t g_pid = getpid();

std::string curr_td() {
  char buffer[26];
  int millisec;
  struct tm* tm_info;
  struct timeval tv;

  gettimeofday(&tv, NULL);

  millisec = lrint(tv.tv_usec/1000.0); // Round to nearest millisec
  if (millisec>=1000) { // Allow for rounding up to nearest second
    millisec -=1000;
    tv.tv_sec++;
  }

  tm_info = localtime(&tv.tv_sec);
  strftime(buffer, 26, "%Y:%m:%d %H:%M:%S", tm_info);
  std::stringstream ss;
  ss << buffer << "." << millisec << " " << g_pid << ": ";
  return ss.str();
}


namespace mesos {
namespace internal {

class CommandExecutorProcess // : public Process<CommandExecutorProcess>
{
public:
  CommandExecutorProcess() : timer(this) {
    cout << curr_td() << "CommandExecutorProcess::CommandExecutorProcess" << endl;
  }

  virtual ~CommandExecutorProcess() {
    cout << curr_td() << "CommandExecutorProcess::~CommandExecutorProcess" << endl;
  }

  void registered(
      ExecutorDriver* /*driver*/,
      const ExecutorInfo& /*executorInfo*/,
      const FrameworkInfo& /*frameworkInfo*/,
      const SlaveInfo& slaveInfo)
  {
    cout << curr_td() << "CommandExecutorProcess::registered: Registered executor on " << slaveInfo.hostname() << endl;
  }

  void reregistered(
      ExecutorDriver* /*driver*/,
      const SlaveInfo& slaveInfo)
  {
    cout << curr_td() << "CommandExecutorProcess::reregistered: Re-registered executor on " << slaveInfo.hostname() << endl;
  }

  void disconnected(ExecutorDriver* /*driver*/) {}

  void launchTask(ExecutorDriver* driver, const TaskInfo& task)
  {
    if (launched) {
      cout << curr_td() << "CommandExecutorProcess::launchTask: Attempted to run multiple tasks using a \"command\" executor" << endl;
      TaskStatus status;
      status.mutable_task_id()->MergeFrom(task.task_id());
      status.set_state(TASK_FAILED);
      status.set_message(
          "Attempted to run multiple tasks using a \"command\" executor");

      driver->sendStatusUpdate(status);
      return;
    }

    CHECK(task.has_command()) << "CommandExecutorProcess::launchTask: Expecting task " << task.task_id().value()
                              << " to have a command!";

    cout << curr_td() << "CommandExecutorProcess::launchTask: Starting task " << task.task_id().value() << endl;

    // TODO(benh): Clean this up with the new 'Fork' abstraction.
    // Use pipes to determine which child has successfully changed
    // session. This is needed as the setsid call can fail from other
    // processes having the same group id.
    int pipes[2];
    if (pipe(pipes) < 0) {
      perror("CommandExecutorProcess::launchTask: Failed to create a pipe");
      abort();
    }

    // Set the FD_CLOEXEC flags on these pipes
    Try<Nothing> cloexec = os::cloexec(pipes[0]);
    if (cloexec.isError()) {
      cerr << curr_td() << "CommandExecutorProcess::launchTask: Failed to cloexec(pipe[0]): " << cloexec.error()
                << endl;
      abort();
    }

    cloexec = os::cloexec(pipes[1]);
    if (cloexec.isError()) {
      std::cerr << curr_td() << "CommandExecutorProcess::launchTask: Failed to cloexec(pipe[1]): " << cloexec.error()
                << endl;
      abort();
    }

    if ((pid = fork()) == -1) {
      std::cerr << curr_td() << "CommandExecutorProcess::launchTask: Failed to fork to run '" << task.command().value() << "': "
                << strerror(errno) << endl;
      abort();
    }

    if (pid != 0) {
        // This works because we can only have one driver and one task id
        gDriver = driver;
        gTaskId = task.task_id();
        timer.delay(Seconds(1), &CommandExecutorProcess::checkChild);
    } else {
      // URB: We don't need to do this since we are already a session leader under the runner
#if 0 //Stock mesos
      // In child process, we make cleanup easier by putting process
      // into it's own session.
      os::close(pipes[0]);

      // NOTE: We setsid() in a loop because setsid() might fail if another
      // process has the same process group id as the calling process.
      while ((pid = setsid()) == -1) {
        perror("Could not put command in its own session, setsid");

        std::cout << "CommandExecutorProcess: Forking another process and retrying" << std::endl;

        if ((pid = fork()) == -1) {
          perror("Failed to fork to launch command");
          abort();
        }

        if (pid > 0) {
          // In parent process. It is ok to suicide here, because
          // we're not watching this process.
          exit(0);
        }
      }

      if (write(pipes[1], &pid, sizeof(pid)) != sizeof(pid)) {
        perror("Failed to write PID on pipe");
        abort();
      }
#endif

      os::close(pipes[1]);

      // The child has successfully setsid, now run the command.
      cout << curr_td() << "sh -c '" << task.command().value() << "'" << endl;
      execl("/bin/sh", "sh", "-c",
            task.command().value().c_str(), (char*) NULL);
      perror("CommandExecutorProcess::launchTask: Failed to exec");
      abort();
    }

    os::close(pipes[1]);

// URB: Don't need to read the pid from a pipe since we aren't double forking
#if 0 // Stock Mesos
    // Get the child's pid via the pipe.
    if (read(pipes[0], &pid, sizeof(pid)) == -1) {
      std::cerr << "Failed to get child PID from pipe, read: "
                << strerror(errno) << std::endl;
      abort();
    }
#endif
    os::close(pipes[0]);

    cout << curr_td() << "Forked command at " << pid << endl;

    // Monitor this process.
#if 0 //stock mesos
    process::reap(pid)
      .onAny(defer(self(),
                   &Self::reaped,
                   driver,
                   task.task_id(),
                   pid,
                   lambda::_1));
#endif

    TaskStatus status;
    status.mutable_task_id()->MergeFrom(task.task_id());
    status.set_state(TASK_RUNNING);
    driver->sendStatusUpdate(status);

    launched = true;
  }

  void killTask(ExecutorDriver* driver, const TaskID& /*taskId*/)
  {
    cout << curr_td() << "CommandExecutorProcess::killTask" << endl;
    shutdown(driver);
//    driver->stop(); //ST do not stop driver here since it wiil disable delivering task status update in checkChild()
                      //   and driver will be stopped anyway in checkChild() after delivering status update
    cout << curr_td() << "CommandExecutorProcess::killTask: end" << endl;
  }

  void frameworkMessage(ExecutorDriver* /*driver*/, const string& /*data*/)
  {
    cout << curr_td() << "CommandExecutorProcess::frameworkMessage" << endl;
  }

  void shutdown(ExecutorDriver* /*driver*/)
  {
    cout << curr_td() << "CommandExecutorProcess::shutdown: Shutting down" << endl;
    // if executor doesn't send TASK_FINISHED then it can be killed here before it actually exits
    // by sleeping and calling checkChild() here we can try to determine exit executor status
    // and send TASK_FINISHED to scheduler
#if 0
    checkChild();
    os::sleep(Seconds(1));
    std::cout << "Shutting down, 1 sec after" << std::endl;
    checkChild();
#endif
    // TODO(benh): Do kill escalation (begin with SIGTERM, after n
    // seconds escalate to SIGKILL).
    if (pid > 0 && !killed) {
      cout << curr_td() << "CommandExecutorProcess::shutdown: Killing process tree at pid " << pid << endl;

      Try<std::list<os::ProcessTree> > trees =
        os::killtree(pid, SIGKILL, true, true);

      if (trees.isError()) {
        cerr << curr_td() << "CommandExecutorProcess::shutdown: Failed to kill the process tree rooted at pid "
             << pid << ": " << trees.error() << endl;
      } else {
        cout << curr_td() << "CommandExecutorProcess::shutdown: Killed the following process trees:\n"
                  << stringify(trees.get()) << endl;
      }

      killed = true;
    }
    cout << curr_td() << "CommandExecutorProcess::shutdown: end" << endl;
  }

  virtual void error(ExecutorDriver* /*driver*/, const string& /*message*/) {}

private:
  void checkChild()
  {
    TaskState state;
    string message;
    int status;

    //cout << "Check child" << endl;
#if 1
    if (waitpid(pid, &status, WNOHANG) <= 0) {
        // Not done yet
        timer.delay(Seconds(1), &CommandExecutorProcess::checkChild);
        return;
    }

    CHECK(WIFEXITED(status) || WIFSIGNALED(status)) << status;

    if (WIFEXITED(status) && WEXITSTATUS(status) == 0) {
      state = TASK_FINISHED;
    } else if (killed) {
      // Send TASK_KILLED if the task was killed as a result of
      // killTask() or shutdown().
      state = TASK_KILLED;
    } else {
      state = TASK_FAILED;
    }
#else // Spark case: if it's called from shutdown() waitpid returns -1 (error) though executor sucessfuly finished
      // set state to TASK_FINISHED since usually that's the case, but status update still douen't get delivered to
      // scheduler
    auto ret = waitpid(pid, &status, WNOHANG);
    cout << "ret=" << ret << ", pid teminated normally=" << WIFEXITED(status) << ", exit status=" << WEXITSTATUS(status)
         << ", signelled=" << WIFSIGNALED(status) << ", signal=" << WTERMSIG(status)
         << ", coredumped=" << WCOREDUMP(status) << ", stopped=" << WIFSTOPPED(status)
         << ", stopsignal=" << WSTOPSIG(status) << ", continued=" << WIFCONTINUED(status) << endl;
    if (ret == 0) {
      // Not done yet
      timer.delay(Seconds(1), &CommandExecutorProcess::checkChild);
      cout << "Check child: not done yet, re-checking in 1 sec" << endl;
      return;
    } else if (ret == -1) {
      cout << "Check child: cannot determine child exit status, assuming success" << endl;
    }

    CHECK(WIFEXITED(status) || WIFSIGNALED(status)) << status;

    if (WIFEXITED(status) && WEXITSTATUS(status) == 0) {
      state = TASK_FINISHED;
      cout << "Check child: TASK_FINISHED" << endl;
    } else if (killed) {
      // Send TASK_KILLED if the task was killed as a result of
      // killTask() or shutdown().
      state = TASK_KILLED;
      cout << "Check child: TASK_KILLED" << endl;
    } else if (ret == -1) {
      state = TASK_FINISHED;
      cout << "Check child: TASK_FINISHED, though ret=-1" << endl;      
    } else {
      state = TASK_FAILED;
      cout << "Check child: TASK_FAILED" << endl;
    }
#endif
    message = string("CommandExecutorProcess::checkChild: Command") +
        (WIFEXITED(status)
        ? " exited with status "
        : " terminated with signal ") +
        (WIFEXITED(status)
        ? stringify(WEXITSTATUS(status))
        : strsignal(WTERMSIG(status)));

    cout << curr_td() << message << " (pid: " << pid << ")" << endl;

    TaskStatus taskStatus;
    taskStatus.mutable_task_id()->MergeFrom(gTaskId);
    taskStatus.set_state(state);
    taskStatus.set_message(message);

    cout << curr_td() << "CommandExecutorProcess::checkChild: sending status update for task "
         << gTaskId.value() << " with state " << TaskState_Name(state) << endl;
    gDriver->sendStatusUpdate(taskStatus);

    // A hack for now ... but we need to wait until the status update
    // is sent to the slave before we shut ourselves down.
    os::sleep(Seconds(1));
    cout << curr_td() << "CommandExecutorProcess::checkChild: before driver stop" << endl;
    gDriver->stop();
    cout << curr_td() << "CommandExecutorProcess::checkChild: after driver stop" << endl;
  }

  bool launched = false;
  bool killed = false;
  pid_t pid = -1;
  liburb::Timer<CommandExecutorProcess> timer;
  ExecutorDriver* gDriver = nullptr;
  TaskID gTaskId;
};


class CommandExecutor: public Executor
{
public:
  CommandExecutor()
  {
    process = new CommandExecutorProcess();
#if 0 //Stock mesos
    spawn(process);
#endif
  }

  virtual ~CommandExecutor()
  {
#if 0 //Stock mesos
    terminate(process);
    wait(process);
#endif
    delete process;
  }

  virtual void registered(
        ExecutorDriver* driver,
        const ExecutorInfo& executorInfo,
        const FrameworkInfo& frameworkInfo,
        const SlaveInfo& slaveInfo)
  {
#if 0 // Stock mesos
    dispatch(process,
             &CommandExecutorProcess::registered,
             driver,
             executorInfo,
             frameworkInfo,
             slaveInfo);
#else
    process->registered(driver,executorInfo,frameworkInfo,slaveInfo);
#endif
  }

  virtual void reregistered(
      ExecutorDriver* driver,
      const SlaveInfo& slaveInfo)
  {
#if 0 // Stock mesos
    dispatch(process,
             &CommandExecutorProcess::reregistered,
             driver,
             slaveInfo);
#else
    process->reregistered(driver,slaveInfo);
#endif
  }

  virtual void disconnected(ExecutorDriver* driver)
  {
#if 0 // Stock mesos
    dispatch(process, &CommandExecutorProcess::disconnected, driver);
#else
    process->disconnected(driver);
#endif
  }

  virtual void launchTask(ExecutorDriver* driver, const TaskInfo& task)
  {
    //cout << "CommandExecutor: launchTask" << endl;
#if 0 // Stock mesos
    dispatch(process, &CommandExecutorProcess::launchTask, driver, task);
#else
    process->launchTask(driver,task);
#endif
  }

  virtual void killTask(ExecutorDriver* driver, const TaskID& taskId)
  {
#if 0 // Stock mesos
    dispatch(process, &CommandExecutorProcess::killTask, driver, taskId);
#else
    process->killTask(driver,taskId);
#endif
  }

  virtual void frameworkMessage(ExecutorDriver* driver, const string& data)
  {
#if 0 // Stock mesos
    dispatch(process, &CommandExecutorProcess::frameworkMessage, driver, data);
#else
    process->frameworkMessage(driver,data);
#endif
  }

  virtual void shutdown(ExecutorDriver* driver)
  {
    //cout << "CommandExecutor: shutdown" << endl;
#if 0 // Stock mesos
    dispatch(process, &CommandExecutorProcess::shutdown, driver);
#else
    process->shutdown(driver);
#endif
  }

  virtual void error(ExecutorDriver* driver, const string& data)
  {
#if 0 // Stock mesos
    dispatch(process, &CommandExecutorProcess::error, driver, data);
#else
    process->error(driver,data);
#endif
  }

private:
  CommandExecutorProcess* process;
};

} // namespace internal {
} // namespace mesos {


int main(int /*argc*/, char** /*argv*/)
{
  mesos::internal::CommandExecutor executor;
  mesos::MesosExecutorDriver driver(&executor);
  cout << curr_td() << "command_executor: About to call driver.run()" << endl;
  auto ret = driver.run();
  cout << curr_td() << "command_executor: end: driver returned " << ret << endl;
  return ret == mesos::DRIVER_STOPPED ? 0 : 1;
//  return driver.run() == mesos::DRIVER_STOPPED ? 0 : 1;
}
