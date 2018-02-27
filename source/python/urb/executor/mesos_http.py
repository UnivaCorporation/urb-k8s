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


from flask import Flask, request, Response, stream_with_context
from gevent.wsgi import WSGIServer
import gevent
import json
from google.protobuf import json_format
from google.protobuf import descriptor_pb2
from google.protobuf import descriptor
from google.protobuf import reflection

#import mesos_pb2
#import scheduler_pb2

from urb.log.log_manager import LogManager

from gevent import monkey
monkey.patch_socket()
#monkey.patch_all()

app = Flask(__name__)
#app.debug = True

logger = LogManager.get_instance().get_logger(__name__)


def request_debug(msg, request):
    logger.debug("%s: request=%s" % (msg, request))
    logger.debug("is_json: %s" % request.is_json)
    logger.debug("request.headers=%s" % request.headers)
    logger.debug("request.environ=%s" % request.environ)
    logger.debug("request.data=%s" % request.data)


@app.route('/redirect', methods=['GET', 'POST'])
def redirect():
    request_debug("/redirect", request)
    resp = Response(status=200)
    return resp

@app.route('/monitor/statistics', methods=['GET'])
def statistics():
    try:
        request_debug("Get monitor/statistics", request)
        s_json = json.dumps([])
        if True:
#        if request.is_json:
            resp = Response(s_json, status=200, mimetype="application/json")
        else:
            resp = Response(status=404)
        return resp
    except Exception as e:
        msg = "Exception handling %s: %s" % (request.url_rule, e)
        logger.error(msg)
        return Response(msg, status=500)

@app.route('/slave(1)/state', methods=['GET'])
def slave1_state():
    try:
        request_debug("Get /slave(1)/state", request)
        mesos_handler = MesosHttp.get_mesos_handler()
        s_json = json.dumps({
            'version' :  executor_handler.MESOS_VERSION,
            'flags' : {}
            })
        if True:
#        if request.is_json:
            resp = Response(s_json, status=200, mimetype="application/json")
        else:
            resp = Response(status=404)
        return resp
    except Exception as e:
        msg = "Exception handling %s: %s" % (request.url_rule, e)
        logger.error(msg)
        return Response(msg, status=500)

class MesosHttp:
    executor_handler = None

    def __init__(self, port=5061):
        self.name = self.__class__.__name__
        self.port = port
        self.logger = LogManager.get_instance().get_logger(self.name)
        self.logger.info("__init__")

    @classmethod
    def get_executor_handler(cls):
        return cls.executor_handler

    def start(self, executor_handler):
        self.logger.info("Starting http server on port %d" % self.port)
        self.__class__.executor_handler = mesos_handler
#        self.__http_thread = gevent.spawn(app.run(host='0.0.0.0', port=self.port))
        self.__wsgi = WSGIServer(('', self.port), app)
        self.__http_thread = gevent.spawn(self.__wsgi.serve_forever)
        self.logger.debug("Spawned http server thread")

    def stop(self):
        self.logger.info("Stopping http server")
        self.shutdown()

    def shutdown(self):
        self.__wsgi.stop()
