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
#from protobuf_to_dict import protobuf_to_dict

import mesos_pb2
import scheduler_pb2

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

@app.route('/master/state', methods=['GET'])
@app.route('/state', methods=['GET'])
def state():
    try:
        request_debug("Get state", request)
        mesos_handler = MesosHttp.get_mesos_handler()
        state_json = json.dumps({
            'version' : mesos_handler.MESOS_VERSION,
            'cluster' : 'urb-uge-cluster',
            'flags' : {},
            'slaves' : [],
            'frameworks' : [],
            'completed_frameworks' : [],
            'orphan_tasks' : [],
            'unregistered_frameworks' : []
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
                descriptor_proto.field.add(name='cluster',
                                                number=2,
                                                type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
                                                label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL)
                desc = descriptor.MakeDescriptor(descriptor_proto)
                clazz = reflection.MakeClass(desc)
                msg = clazz(version=mesos_handler.MESOS_VERSION,
                            cluster='urb-uge-cluster')
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

@app.route('/master/slaves', methods=['GET'])
@app.route('/slaves', methods=['GET'])
def slaves():
    try:
        request_debug("Get slaves", request)
#        slaves_json = json.dumps(
#        {"slaves":[{"id":"2d24a9aa-b496-40cf-a6d9-74e36b246c65-S0","hostname":"head.private","port":5051,"attributes":{},"pid":"slave(1)@10.0.2.15:5051","registered_time":1517236098.85274,"resources":{"disk":13778.0,"mem":2719.0,"gpus":0.0,"cpus":1.0,"ports":"[31000-32000]"},"used_resources":{"disk":0.0,"mem":0.0,"gpus":0.0,"cpus":0.0},"offered_resources":{"disk":0.0,"mem":0.0,"gpus":0.0,"cpus":0.0},"reserved_resources":{},"unreserved_resources":{"disk":13778.0,"mem":2719.0,"gpus":0.0,"cpus":1.0,"ports":"[31000-32000]"},"active":True,"version":"1.4.0","capabilities":["MULTI_ROLE","HIERARCHICAL_ROLE","RESERVATION_REFINEMENT"],"reserved_resources_full":{},"unreserved_resources_full":[{"name":"cpus","type":"SCALAR","scalar":{"value":1.0},"role":"*"},{"name":"mem","type":"SCALAR","scalar":{"value":2719.0},"role":"*"},{"name":"disk","type":"SCALAR","scalar":{"value":13778.0},"role":"*"},{"name":"ports","type":"RANGES","ranges":{"range":[{"begin":31000,"end":32000}]},"role":"*"}],"used_resources_full":[],"offered_resources_full":[]}],"recovered_slaves":[]}
#        )
        slaves_json = json.dumps({'slaves' : []})
        if request.is_json:
            resp = Response(slaves_json, status=200, mimetype="application/json")
        else:
            resp = Response(status=404)
#            msg = json_format.Parse(slaves_json, xxx_pb2.Event(), ignore_unknown_fields=False)
#            resp = Response(msg, status=200, mimetype="application/x-protobuf")
        return resp
    except Exception as e:
        msg = "Exception handling %s: %s" % (request.url_rule, e)
        logger.error(msg)
        return Response(msg, status=500)

@app.route('/master/racks', methods=['GET'])
@app.route('/racks', methods=['GET'])
def racks():
    try:
        request_debug("Get racks", request)
#        racks = json.dumps({
#            'racks' : [ { 'id' : 'dummy' } ]
#        })
#        resp = Response(racks, status=200, mimetype="application/json" if request.is_json else "application/x-protobuf")
        resp = Response(status=404) # return "not found" as mesos does
        return resp
    except Exception as e:
        msg = "Exception handling %s: %s" % (request.url_rule, e)
        logger.error(msg)
        return Response(msg, status=500)

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
            'version' :  mesos_handler.MESOS_VERSION,
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

@app.route('/api/v1/scheduler', methods=['GET', 'POST'])
@app.route('/master/api/v1/scheduler', methods=['GET', 'POST'])
def scheduler():
    mesos_handler = MesosHttp.get_mesos_handler()
    request_debug("/api/v1/scheduler", request)
    try:
        if request.method == 'POST':
            logger.info("POST")
            content = {}
            if request.is_json:
                logger.debug("json data")
                content = request.get_json()
                ctype = content['type']
            else:
                logger.debug("protobuf data")
                call = scheduler_pb2.Call()
                call.ParseFromString(request.data)
#                content = protobuf_to_dict(call, use_enum_labels=True)
                content = json_format.MessageToDict(call, preserving_proto_field_name = True)
            logger.info("content=%s" % content)
            if content['type'] == 'SUBSCRIBE':
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
#                        master_info['port'] = mesos_handler.get_http_port() # set actual http port (instead of redis port)
#                        master_info['address']['port'] = master_info['port']
                        
#                        if 'ip' in master_info:
#                            del master_info['ip'] # might be incorrect

                        subscribed_json = json.dumps({
                            'type'         : 'SUBSCRIBED',
                            'subscribed'   : {
                                'framework_id' : {'value' : framework_name},
                                'heartbeat_interval_seconds' : mesos_handler.get_heartbeat_interval(),
                                'master_info' : master_info
                            }
                        })
                        if request.is_json:
                            subscribed = subscribed_json
                            logger.debug("json subscribed response")
                        else:
                            logger.debug("protobuf subscribed response")
                            subscribed_msg = json_format.Parse(subscribed_json, scheduler_pb2.Event(), ignore_unknown_fields=False)
                            subscribed = subscribed_msg.SerializeToString()

                        length = len(subscribed)
                        buf = str(length) + "\n" + subscribed
                        logger.debug("subscribed=%s, yield it as recordio" % subscribed)
                        yield buf

                        logger.debug("subscribed before generate offer loop")
                        for offers in mesos_handler.http_generate_offers({'value' : framework_name}):
                            if offers:
                                if request.is_json:
                                    resp_event = json.dumps(offers)
                                    logger.debug("json offer response")
                                else:
                                    offer_msg = json_format.Parse(json.dumps(offers), scheduler_pb2.Event(), ignore_unknown_fields=False)
                                    resp_event = offer_msg.SerializeToString()
                                    logger.debug("protobuf offer response")
                                length = len(resp_event)
                                buf = str(length) + "\n" + resp_event
                                logger.debug("offer: %s, yield it as recordio" % resp_event)
                                yield buf
                            else:
                                logger.debug("in offer loop: skip empty offers")
                    except Exception as ge:
                        logger.error("Exception in generator: %s" % ge)

                g = generate()
                framework_name = next(g)
                logger.debug("generated framework_name=%s" % framework_name)
                mimetype = "application/json" if request.is_json else "application/x-protobuf"
#                content_type = "application/json" if is_json_response else "application/x-protobuf"
                resp = Response(stream_with_context(g), status = 200, mimetype = mimetype)
                resp.headers['Mesos-Stream-Id'] = framework_name
                logger.debug("resp.headers=%s" % resp.headers)
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
                    for operation in content['accept']['operations']:
                        if operation['type'] == 'LAUNCH':
                            mesos_handler.http_accept_launch(framework_id, offer_ids, filters, operation['launch'])
                        else:
                            msg = "ACCEPT: operation type %s is not supported" % content['accept']['operations']['type']
                            resp = Response(msg, status=400)
                            return resp
                else:
                    # same as decline
                    mesos_handler.http_decline(framework_id, offer_ids, filters)
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
                agent_id = content['kill'].get('agent_id')
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
                tasks = content.get('reconcile',{}).get('tasks',[])
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
        else:
            logger.info("scheduler: unxpected request method: %s" % request.method)
    except Exception as e:
        msg = "Exception in scheduler endpoint: %s" % e
        logger.error(msg)
        return Response(msg, status=500)

class MesosHttp:
    mesos_handler = None

    def __init__(self, port=5050):
        self.name = self.__class__.__name__
        self.port = port
        self.logger = LogManager.get_instance().get_logger(self.name)
        self.logger.info("__init__")

    @classmethod
    def get_mesos_handler(cls):
        return cls.mesos_handler

    def start(self, mesos_handler):
        self.logger.info("Starting http server on port %d" % self.port)
        self.__class__.mesos_handler = mesos_handler
#        self.__http_thread = gevent.spawn(app.run(host='0.0.0.0', port=self.port))
        self.__wsgi = WSGIServer(('', self.port), app)
        self.__http_thread = gevent.spawn(self.__wsgi.serve_forever)
        self.logger.debug("Spawned http server thread")

    def stop(self):
        self.logger.info("Stopping http server")
        self.shutdown()

    def shutdown(self):
        self.__wsgi.stop()


# Testing
#if __name__ == '__main__':
#    http = MesosHttp()
#    gevent.spawn(app.run(host='0.0.0.0', port=5050))
    