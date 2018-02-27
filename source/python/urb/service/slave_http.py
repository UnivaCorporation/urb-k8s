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
monkey.patch_all()

app = Flask(__name__)
#app.debug = True

logger = LogManager.get_instance().get_logger(__name__)

def request_debug(msg, r):
    logger.debug("%s: request=%s" % (msg, r))
    logger.debug("is_json: %s" % r.is_json)
    logger.debug("request.headers=%s" % r.headers)
    logger.debug("request.environ=%s" % r.environ)
    logger.debug("request.data=%s" % r.data)


@app.route('/redirect', methods=['GET', 'POST'])
def redirect():
    request_debug("/redirect", request)
    resp = Response(status=200)
    return resp

@app.route('/state', methods=['GET'])
@app.route('/slave(1)/state', methods=['GET'])
def state():
    try:
        request_debug("Get slave state", request)
        mesos_handler = SlaveHttp.get_mesos_handler()
        state_json = json.dumps({
            'version' : mesos_handler.MESOS_VERSION,
            'resources' : {},
            'attributes' : {},
            'flags' : {},
            'frameworks' : [],
            'completed_frameworks' : [],
        })
        if True:
#        if request.is_json:
            resp = Response(state_json, status=200, mimetype="application/json")
        else:
            try:
                descriptor_proto = descriptor_pb2.DescriptorProto()
                descriptor_proto.name = "state"
                descriptor_proto.field.add(name='version',
                                                number=1,
                                                type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
                                                label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL)
                desc = descriptor.MakeDescriptor(descriptor_proto)
                clazz = reflection.MakeClass(desc)
                msg = clazz(version=mesos_handler.MESOS_VERSION)
                ser_msg = msg.SerializeToString()
                logger.info("state content=%s" % ser_msg)
    #            msg = json_format.Parse(state_json, xxx_pb2.Event(), ignore_unknown_fields=False)
                resp = Response(ser_msg, status=200, mimetype="application/x-protobuf")
            except Exception as se:
                msg = "Exception: %s" % se
                logger.error(msg)
                return Response(msg, status=500)
        return resp
    except Exception as e:
        msg = "Exception handling: %s" % (request.url_rule, e)
        logger.error(msg)
        return Response(msg, status=500)


@app.route('/monitor/statistics', methods=['GET'])
def statistics():
    try:
        request_debug("Get slave monitor/statistics", request)
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


class SlaveHttp:
    mesos_handler = None

    def __init__(self, port=5051):
        self.name = self.__class__.__name__
        self.port = port
        self.logger = LogManager.get_instance().get_logger(self.name)
        self.logger.info("__init__")

    @classmethod
    def get_mesos_handler(cls):
        return cls.mesos_handler

    def start(self, mesos_handler):
        self.logger.info("Starting http slave server on port %d" % self.port)
        self.__class__.mesos_handler = mesos_handler
        self.__wsgi = WSGIServer(('', self.port), app)
        self.__http_thread = gevent.spawn(self.__wsgi.serve_forever)
        self.logger.debug("Spawned slave http server thread")

    def stop(self):
        self.logger.info("Stopping slave http server")
        self.shutdown()

    def shutdown(self):
        self.__wsgi.stop()


# Testing
#if __name__ == '__main__':
#    http = SlaveHttp()
#    gevent.spawn(app.run(host='0.0.0.0', port=5051))
