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
from flask_socketio import SocketIO, Namespace, emit
#from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer

import gevent
import json
from google.protobuf.json_format import MessageToJson

from protobuf_to_dict import protobuf_to_dict

import mesos_pb2
import scheduler_pb2


from urb.log.log_manager import LogManager
#from urb.service.mesos_handler import MesosHandler
from urb.messaging.mesos.register_framework_message import RegisterFrameworkMessage
from urb.messaging.mesos.subscribe_message import SubscribeMessage
from urb.messaging.mesos.subscribed_message import SubscribedMessage

from gevent import monkey
monkey.patch_all()

app = Flask(__name__)
#app.debug = True
io = SocketIO(app)
#io.debug = True

logger = LogManager.get_instance().get_logger(__name__)

clients = []

def request_debug(endpoint, request):
    logger.debug("%s: request=%s" % (endpoint, request))
    logger.debug("is_json: %s" % request.is_json)
    logger.debug("request.headers=%s" % request.headers)
    logger.debug("request.environ=%s" % request.environ)
    logger.debug("request.data=%s" % request.data)


#class MesosHTTPRequestHandler(BaseHTTPRequestHandler):
#    def do_POST(self):
#        content = self.rfile.read(self.get_length())

@app.route('/redirect', methods=['GET', 'POST'])
def redirect():
    request_debug("/redirect", request)
    resp = Response(status=200)
    return resp

@app.route('/master/state', methods=['GET'])
@app.route('/state', methods=['GET'])
def state():
    request_debug("/master/state", request)
    mesos_handler = MesosHttp.get_mesos_handler()
    state = json.dumps({
        'version' : mesos_handler.MESOS_VERSION,
    })
#    length = len(state)
#    buf = str(length) + "\n" + state
    resp = Response(state, status=200, mimetype="application/json")
#    resp = Response(buf, status=200, mimetype="application/json" if request.is_json else "application/x-protobuf")
    return resp

@app.route('/master/slaves', methods=['GET'])
@app.route('/slaves', methods=['GET'])
def slaves():
    request_debug("/master/slaves", request)
#    slaves = json.dumps({
#        '' : ??
#        })
    resp = Response(status=200, mimetype="application/json")
    return resp

def give_offer():
    offers = json.dumps({'type' : 'OFFERS',
                            'offers' : { 'offers' :
                                [
                                { 'id' : { 'value' : 'offer_id' },
                                'framework_id' : {'value' : 'framework_id'},
                                'agent_id' : {'value' : 'agent_id'},
                                'hostname' : 'head'
                                }]
                                }
                        })
    length = len(offers)
    buf = str(length) + "\n" + offers
    return buf
#    yield buf
    

@app.route('/api/v1/scheduler', methods=['GET', 'POST'])
@app.route('/master/api/v1/scheduler', methods=['GET', 'POST'])
def scheduler():
    mesos_handler = MesosHttp.get_mesos_handler()
#    logger.debug("namespace=%s, sid=%s" % (request.namespace, request.sid))
    request_debug("/api/v1/scheduler", request)
#    io.emit("my response", {'data': 'A NEW FILE WAS POSTED'})
#    logger.debug("in rooms: %s" % io.rooms())
#    logger.debug("in rooms: %s" % flask_socketio.rooms())
#    logger.debug("sessions=%s" % session)
    try:
        if request.method == 'POST':
            logger.info("POST")
            content = {}
            ctype = None
            if request.is_json:
                logger.debug("json data")
                content = request.get_json()
                ctype = content['type']
            else:
                logger.debug("protobuf data")
                try:
                    call = scheduler_pb2.Call()
                    call.ParseFromString(request.data)
    #                m = scheduler_pb2.Call.Subscribe()
    #                m.ParseFromString(request.data)
                    content = protobuf_to_dict(call, use_enum_labels=True)
                    ctype = content['type']
                    logger.debug("ctype=%s" % ctype)
    #                js = MessageToJson(call)
    #                logger.debug("js=%s" % js)
                except Exception as e:
                    logger.error("Exception: %s" % e)
            logger.info("content=%s" % content)
            if ctype == "SUBSCRIBE":
                logger.debug("app_context=%s" % app.app_context())
                framework_id = None
                if "Mesos-Stream-Id" in request.headers:
                    msg = "Subscribe calls should not include the 'Mesos-Stream-Id' header"
                    length = len(msg)
                    buf = str(length) + "\n" + msg
                    resp = Response(buf, status=400)
                    return resp
                def generate():
                    mesos_subscribed = mesos_handler.http_subscribe(content['subscribe']['framework_info'])
                    framework_id = mesos_subscribed['payload']['framework_id']['value']
                    logger.debug("Subscribed framework_id=%s" % framework_id)
                    master_info = mesos_subscribed['payload']['master_info']
                    master_info['port'] = 5050 # override for Mesos http port for now
                    master_info['address']['port'] = 5050
                    
                    del master_info['ip'] # might be incorrect

                    if request.is_json:
                        subscribed = json.dumps({
                            'type'         : 'SUBSCRIBED',
                            'subscribed'   : {
                                'framework_id' : {'value' : framework_id},
                                'heartbeat_interval_seconds' : 15,
                                'master_info' : master_info
                            }
                        })
                    else:
                        subscribed_event = scheduler_pb2.Event()
                        subscribed_event.type = scheduler_pb2.Event.SUBSCRIBED
                        subscribed_event.subscribed.framework_id.value = framework_id
                        subscribed_event.subscribed.heartbeat_interval_seconds = 15
                        subscribed_event.subscribed.master_info.id = master_info['id']
        #                subscribed_event.subscribed.master_info.ip = master_info['ip']
                        subscribed_event.subscribed.master_info.port = master_info['port']
                        subscribed_event.subscribed.master_info.hostname = master_info['hostname']
                        subscribed_event.subscribed.master_info.version = master_info['version']
                        subscribed_event.subscribed.master_info.address.ip = master_info['address']['ip']
                        subscribed_event.subscribed.master_info.address.hostname = master_info['address']['hostname']
                        subscribed_event.subscribed.master_info.address.port = master_info['address']['port']
                        
                        subscribed = subscribed_event.SerializeToString()

                    logger.debug("subscribed=%s" % subscribed)
                    length = len(subscribed)
                    buf = str(length) + "\n" + subscribed
                    logger.debug("subscribed before yield, buf=%s" % buf)
                    yield buf

                    logger.debug("subscribed before generate offer loop")
                    for data in mesos_handler.http_generate_offers({'value' : framework_id}):
                        logger.debug("yielded")
                        if data:
                            resp_event = json.dumps(data)
                            length = len(resp_event)
                            buf = str(length) + "\n" + resp_event
                            logger.debug("in offer loop: before yield, buf=%s" % buf)
                            yield buf
                        else:
                            logger.debug("in offer loop: skip empty data")

    #                while True:
    #                    gevent.sleep(5)
    #                    buf = give_offer()
    #                    yield buf

    #                    offers = mesos_handler.generate_offers({'value' : framework_id}, True)
                        #offers = json.dumps({'type' : 'OFFERS',
                                            #'offers' : { 'offers' :
                                                #[
                                                #{ 'id' : { 'value' : 'offer_id' },
                                                #'framework_id' : {'value' : 'framework_id'},
                                                #'agent_id' : {'value' : 'agent_id'},
                                                #'hostname' : 'head'
                                                #}]
                                                #}
                                            #})
                        #length = len(offers)
                        #buf = str(length) + "\n" + offers
                        #yield buf

    #            resp = Response(buf, status=200, mimetype="application/json" if request.is_json else "application/x-protobuf")
                resp = Response(stream_with_context(generate()), status=200, mimetype="application/json" if request.is_json else "application/x-protobuf")
                resp.headers['Mesos-Stream-Id'] = framework_id
                return resp

            elif content['type'] == 'TEARDOWN':
                logger.debug("TEARDOWN")
                framework_id = content['framework_id']
                
            elif content['type'] == 'ACCEPT':
                logger.debug("ACCEPT")
                framework_id = content['framework_id']
                offer_ids = content['accept']['offer_ids']
                filters = content['accept'].get('filters')
                if content['accept']['operations']['type'] == 'LAUNCH':
                    mesos_handler.http_accept_launch(framework_id, offer_ids, filters, content['accept']['operations']['launch'])
                else:
                    msg = "ACCEPT: operation type %s is not supported" % content['accept']['operations']['type']
                    resp = Response(msg, status=400)
                    return resp
    #            for operation in content['accept']['operations']:
    #                if operation['type'] == 'LAUNCH':
    #                    mesos_handler.accept_launch(framework_id, offer_ids, filters, operation['launch'])
    #                else:
    #                    msg = "ACCEPT: operation type %s is not supported" % operation['type']
    #                    resp = Response(msg, status=400)
    #                    return resp
                resp = Response(status=202)
                return resp
            elif content['type'] == 'DECLINE':
                logger.debug("DECLINE")
                framework_id = content['framework_id']

            elif content['type'] == 'REVIVE':
                logger.debug("REVIVE")
            elif content['type'] == 'KILL':
                logger.debug("KILL")
                framework_id = content['framework_id']
                task_id = content['kill']['task_id']
                agent_id = content['kill']['agent_id']
                mesos_handler.http_kill(framework_id, task_id, agent_id)
                resp = Response(status=202)
                return resp
            elif content['type'] == 'SHUTDOWN':
                logger.debug("SHUTDOWN")
            elif content['type'] == 'ACKNOWLEDGE':
                logger.debug("ACKNOWLEDGE")
            elif content['type'] == 'RECONCILE':
                logger.debug("RECONCILE")
            elif content['type'] == 'MESSAGE':
                logger.debug("MESSAGE")
            elif content['type'] == 'REQUEST':
                logger.debug("REQUEST")
            else:
                logger.error("Unkown content type: %s" % content['type'])
                
        elif request.method == 'GET':
            logger.info("scheduler: GET")
            auth_msg = mesos_handler.get_target_executor("AuthenticateMessage")
            logger.info("auth_msg=%s" % auth_msg)
            return "massa"
        else:
            logger.info("scheduler: unxpected")
    except Exception as se:
        logger.error("Exception in scheduler endpoint: %s" % se)

class MesosHttp:
    mesos_handler = None
#    def __init__(self, mesos_handler, port=5050):
    def __init__(self, port=5050):
        self.name = self.__class__.__name__
        self.port = port
#        self.mesos_handler = None
        self.logger = LogManager.get_instance().get_logger(self.name)
        self.logger.info("__init__")
        #app = Flask(__name__)
        #self.app = Flask(self.name)
        #self.http = WSGIServer(('', 5050), flask_app)

    @classmethod
    def get_mesos_handler(cls):
        return cls.mesos_handler

    def start(self, mesos_handler):
        self.logger.info("Starting http server")
        self.__class__.mesos_handler = mesos_handler
        #self.flask_app.run(host = '0.0.0.0')
        #self.http.serve_forever()

#        self.__http_thread = gevent.spawn(app.run(host='0.0.0.0', port=5050))
        self.__http_thread = gevent.spawn(io.run(app, host='0.0.0.0', port=self.port))
#        io.run(app, host='0.0.0.0', port=5050)

    def stop(self):
        self.logger.info("Stopping http server")
        self.shutdown()

    def shutdown(self):
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()


# Testing
#if __name__ == '__main__':
#    http = MesosHttp()
#    gevent.spawn(app.run(host='0.0.0.0', port=5050))
    