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
#from flask_socketio import SocketIO
#from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from gevent.wsgi import WSGIServer

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
#io = SocketIO(app)
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
    try:
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
    except Exception as se:
        msg = "Exception in state endpoint: %s" % se
        logger.error(msg)
        return Response(msg, status=500)

@app.route('/master/slaves', methods=['GET'])
@app.route('/slaves', methods=['GET'])
def slaves():
    try:
        request_debug("/master/slaves", request)
        slaves = json.dumps(
        {"slaves":[{"id":"2d24a9aa-b496-40cf-a6d9-74e36b246c65-S0","hostname":"head.private","port":5051,"attributes":{},"pid":"slave(1)@10.0.2.15:5051","registered_time":1517236098.85274,"resources":{"disk":13778.0,"mem":2719.0,"gpus":0.0,"cpus":1.0,"ports":"[31000-32000]"},"used_resources":{"disk":0.0,"mem":0.0,"gpus":0.0,"cpus":0.0},"offered_resources":{"disk":0.0,"mem":0.0,"gpus":0.0,"cpus":0.0},"reserved_resources":{},"unreserved_resources":{"disk":13778.0,"mem":2719.0,"gpus":0.0,"cpus":1.0,"ports":"[31000-32000]"},"active":True,"version":"1.4.0","capabilities":["MULTI_ROLE","HIERARCHICAL_ROLE","RESERVATION_REFINEMENT"],"reserved_resources_full":{},"unreserved_resources_full":[{"name":"cpus","type":"SCALAR","scalar":{"value":1.0},"role":"*"},{"name":"mem","type":"SCALAR","scalar":{"value":2719.0},"role":"*"},{"name":"disk","type":"SCALAR","scalar":{"value":13778.0},"role":"*"},{"name":"ports","type":"RANGES","ranges":{"range":[{"begin":31000,"end":32000}]},"role":"*"}],"used_resources_full":[],"offered_resources_full":[]}],"recovered_slaves":[]}
        )
#        slaves = json.dumps({
#            'slaves' : [ {'id' : 'dummy'},
#                         {'hostname' : 'dummy'},
#                         {'port' : 5051},
#                         {'active' : True},
#                         {'version' : '1.4.0'}
#                       ]
#        })
        resp = Response(slaves, status=200, mimetype="application/json")
        return resp
    except Exception as se:
        msg = "Exception in slaves endpoint: %s" % se
        logger.error(msg)
        return Response(msg, status=500)

@app.route('/master/racks', methods=['GET'])
@app.route('/racks', methods=['GET'])
def racks():
    try:
        request_debug("/master/racks", request)
#        racks = json.dumps({
#            'racks' : [ { 'id' : 'dummy' } ]
#        })
#        resp = Response(racks, status=200, mimetype="application/json")
        resp = Response(status=404) # return "not found" as mesos does
        return resp
    except Exception as se:
        msg = "Exception in racks endpoint: %s" % se
        logger.error(msg)
        return Response(msg, status=500)


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
                if "Mesos-Stream-Id" in request.headers:
                    msg = "Subscribe calls should not include the 'Mesos-Stream-Id' header"
                    length = len(msg)
                    buf = str(length) + "\n" + msg
                    resp = Response(buf, status=400)
                    return resp
                def generate():
                    try:
                        mesos_subscribed = mesos_handler.http_subscribe(content['subscribe']['framework_info'])
                        framework_name = mesos_subscribed['payload']['framework_id']['value']
                        logger.debug("Subscribed framework_name=%s, yield it" % framework_name)
                        yield framework_name
                        master_info = mesos_subscribed['payload']['master_info']
                        master_info['port'] = mesos_handler.get_http_port() # set actual http port (instead of redis port)
                        master_info['address']['port'] = master_info['port']
                        
#                        if 'ip' in master_info:
#                            del master_info['ip'] # might be incorrect

                        if request.is_json:
                            subscribed = json.dumps({
                                'type'         : 'SUBSCRIBED',
                                'subscribed'   : {
                                    'framework_id' : {'value' : framework_name},
                                    'heartbeat_interval_seconds' : mesos_handler.get_heartbeat_interval(),
                                    'master_info' : master_info
                                }
                            })
                        else:
                            subscribed_event = scheduler_pb2.Event()
                            subscribed_event.type = scheduler_pb2.Event.SUBSCRIBED
                            subscribed_event.subscribed.framework_id.value = framework_name
                            subscribed_event.subscribed.heartbeat_interval_seconds = mesos_handler.get_heartbeat_interval()
                            subscribed_event.subscribed.master_info.id = master_info['id']
                            subscribed_event.subscribed.master_info.ip = master_info['ip']
                            subscribed_event.subscribed.master_info.port = master_info['port']
                            subscribed_event.subscribed.master_info.hostname = master_info['hostname']
                            subscribed_event.subscribed.master_info.version = master_info['version']
                            subscribed_event.subscribed.master_info.address.ip = master_info['address']['ip']
                            subscribed_event.subscribed.master_info.address.hostname = master_info['address']['hostname']
                            subscribed_event.subscribed.master_info.address.port = master_info['address']['port']

                            subscribed = subscribed_event.SerializeToString()

                        length = len(subscribed)
                        buf = str(length) + "\n" + subscribed
                        logger.debug("subscribed=%s, yield it as recordio" % subscribed)
                        yield buf

                        logger.debug("subscribed before generate offer loop")
                        for data in mesos_handler.http_generate_offers({'value' : framework_name}):
                            if data:
                                resp_event = json.dumps(data)
                                length = len(resp_event)
                                buf = str(length) + "\n" + resp_event
                                logger.debug("offer: %s, yield it as recordio" % resp_event)
                                yield buf
                            else:
                                logger.debug("in offer loop: skip empty data")
                    except Exception as ge:
                        logger.error("Exception in generator: %s" % ge)

                g = generate()
                framework_name = next(g)
                logger.debug("framework_name=%s" % framework_name)
                resp = Response(stream_with_context(g), status=200, headers = {'Mesos-Stream-Id' : framework_name}, mimetype="application/json" if request.is_json else "application/x-protobuf")
#                resp.headers['Mesos-Stream-Id'] = framework_name
                return resp

            elif content['type'] == 'TEARDOWN':
                logger.debug("TEARDOWN")
                framework_id = content['framework_id']
                mesos_handler.http_teardown(framework_id)
                resp = Response(status=202)
                return resp
                
            elif content['type'] == 'ACCEPT':
                logger.debug("ACCEPT")
                framework_id = content['framework_id']
                offer_ids = content['accept']['offer_ids']
                filters = content['accept'].get('filters')
                if content['accept'].get('operations') and len(content['accept']['operations']) > 0:
                    if content['accept']['operations']['type'] == 'LAUNCH':
                        mesos_handler.http_accept_launch(framework_id, offer_ids, filters, content['accept']['operations']['launch'])
                    else:
                        msg = "ACCEPT: operation type %s is not supported" % content['accept']['operations']['type']
                        resp = Response(msg, status=400)
                        return resp
                else:
                    # same as decline
                    mesos_handler.http_decline(framework_id, offer_ids, filters)
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
                offer_ids = content['decline']['offer_ids']
                filters = content['decline'].get('filters')
                mesos_handler.http_decline(framework_id, offer_ids, filters)
                resp = Response(status=202)
                return resp

            elif content['type'] == 'REVIVE':
                logger.debug("REVIVE")
                framework_id = content['framework_id']
                revive = content['revive']
                mesos_handler.http_revive(framework_id, revive)
                resp = Response(status=202)
                return resp

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
                framework_id = content['framework_id']
                executor_id = content['shutdown']['executor_id']
                agent_id = content['shutdown']['agent_id']
                mesos_handler.http_shutdown(framework_id, executor_id, agent_id)
                resp = Response(status=202)
                return resp

            elif content['type'] == 'ACKNOWLEDGE':
                logger.debug("ACKNOWLEDGE")
                framework_id = content['framework_id']
                agent_id = content['acknowledge']['agent_id']
                task_id = content['acknowledge']['task_id']
                uuid = content['acknowledge'].get('uuid')
                mesos_handler.http_acknowledge(framework_id, agent_id, task_id, uuid)
                resp = Response(status=202)
                return resp

            elif content['type'] == 'RECONCILE':
                logger.debug("RECONCILE")
                framework_id = content['framework_id']
                tasks = content['reconcile']['tasks']
                mesos_handler.http_reconcile(framework_id, tasks)
                resp = Response(status=202)
                return resp

            elif content['type'] == 'MESSAGE':
                logger.debug("MESSAGE")
                framework_id = content['framework_id']
                agent_id = content['message']['agent_id']
                executor_id = content['message']['executor_id']
                data = content['message']['data']
                mesos_handler.http_message(framework_id, agent_id, executor_id, data)
                resp = Response(status=202)
                return resp

            elif content['type'] == 'REQUEST':
                logger.debug("REQUEST")
                framework_id = content['framework_id']
                agent_id = content['requests']['agent_id']
                resources = content['requests']['resources']
                mesos_handler.http_request(framework_id, agent_id, resources)
                resp = Response(status=202)
                return resp

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
        msg = "Exception in scheduler endpoint: %s" % se
        logger.error(msg)
        return Response(msg, status=500)

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
        self.logger.info("Starting http server on port %d" % self.port)
        self.__class__.mesos_handler = mesos_handler
        #self.flask_app.run(host = '0.0.0.0')
        #self.http.serve_forever()

#        self.__http_thread = gevent.spawn(app.run(host='0.0.0.0', port=self.port))
#        self.__http_thread = gevent.spawn(io.run(app, host='0.0.0.0', port=self.port))
        self.__wsgi = WSGIServer(('', self.port), app)
        self.__http_thread = gevent.spawn(self.__wsgi.serve_forever)
#        io.run(app, host='0.0.0.0', port=5050)
        self.logger.debug("Spawned http server thread")

    def stop(self):
        self.logger.info("Stopping http server")
        self.shutdown()

    def shutdown(self):
        self.__wsgi.stop()
#        func = request.environ.get('werkzeug.server.shutdown')
#        if func is None:
#            raise RuntimeError('Not running with the Werkzeug Server')
#        func()


# Testing
#if __name__ == '__main__':
#    http = MesosHttp()
#    gevent.spawn(app.run(host='0.0.0.0', port=5050))
    