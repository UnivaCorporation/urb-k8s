#!/usr/bin/env python
# ___INFO__MARK_BEGIN__
# ############################################################################
#
# This code is the Property, a Trade Secret and the Confidential Information
#  of Univa Corporation.
#
#  Copyright Univa Corporation. All Rights Reserved. Access is Restricted.
#
#  It is provided to you under the terms of the
#  Univa Term Software License Agreement.
#
#  If you have any questions, please contact our Support Department.
#
#  www.univa.com
#
###########################################################################
#___INFO__MARK_END__


# Service receives from framework
MESOS_AUTHENTICATE_MESSAGE = 'AuthenticateMessage'
MESOS_DEACTIVATE_FRAMEWORK_MESSAGE = 'DeactivateFrameworkMessage'
MESOS_EXITED_EXECUTOR_MESSAGE = 'ExitedExecutorMessage'
MESOS_FRAMEWORK_TO_EXECUTOR_MESSAGE = 'FrameworkToExecutorMessage'
MESOS_EXECUTOR_TO_FRAMEWORK_MESSAGE = 'ExecutorToFrameworkMessage'
MESOS_KILL_TASK_MESSAGE = 'KillTaskMessage'
MESOS_RECONCILE_TASKS_MESSAGE = 'ReconcileTasksMessage'
MESOS_REGISTER_FRAMEWORK_MESSAGE = 'RegisterFrameworkMessage'
MESOS_REGISTER_SLAVE_MESSAGE = 'RegisterSlaveMessage'
MESOS_REREGISTER_FRAMEWORK_MESSAGE = 'ReregisterFrameworkMessage'
MESOS_REREGISTER_SLAVE_MESSAGE = 'ReregisterSlaveMessage'
MESOS_RESOURCE_REQUEST_MESSAGE = 'ResourceRequestMessage'
MESOS_REVIVE_OFFERS_MESSAGE = 'ReviveOffersMessage'
MESOS_STATUS_UPDATE_ACKNOWLEDGEMENT_MESSAGE = \
    'StatusUpdateAcknowledgementMessage'
MESOS_STATUS_UPDATE_MESSAGE = 'StatusUpdateMessage'
MESOS_SUBMIT_SCHEDULER_REQUEST_MESSAGE = 'SubmitSchedulerRequest'
MESOS_UNREGISTER_FRAMEWORK_MESSAGE = 'UnregisterFrameworkMessage'
MESOS_UNREGISTER_SLAVE_MESSAGE = 'UnregisterSlaveMessage'

# Service sends to framework
MESOS_FRAMEWORK_REGISTERED_MESSAGE = 'FrameworkRegisteredMessage'
MESOS_FRAMEWORK_REREGISTERED_MESSAGE = 'FrameworkReregisteredMessage'
MESOS_RESOURCE_OFFERS_MESSAGE = 'ResourceOffersMessage'
MESOS_RESCIND_RESOURCE_OFFER_MESSAGE = 'RescindResourceOfferMessage'

# Service sends to executor
MESOS_RUN_TASK_MESSAGE = 'RunTaskMessage'
MESOS_SHUTDOWN_EXECUTOR_MESSAGE = "ShutdownExecutorMessage"

# Service receives from framework and sends to executor runner
MESOS_LAUNCH_TASKS_MESSAGE = 'LaunchTasksMessage'

# Service receives from executor runner 
MESOS_REGISTER_EXECUTOR_RUNNER_MESSAGE = 'RegisterExecutorRunnerMessage'

# Service receives from executor
MESOS_REGISTER_EXECUTOR_MESSAGE = 'RegisterExecutorMessage'
MESOS_REREGISTER_EXECUTOR_MESSAGE = 'ReregisterExecutorMessage'

# Executor runner sends to the service and service sends to the executor
MESOS_EXECUTOR_REGISTERED_MESSAGE = 'ExecutorRegisteredMessage'
MESOS_EXECUTOR_REREGISTERED_MESSAGE = 'ExecutorReregisteredMessage'
