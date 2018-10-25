# -*- coding: utf-8 -*-

import json, uuid
from collections import namedtuple
from ws4py.client.threadedclient import WebSocketClient

class RosBridgeClient(WebSocketClient):

    def __init__(self, url):
        self.callbacks = {}
        self.serviceCallbacks = {}
        super(RosBridgeClient, self).__init__(url)

    def subscribe(self, topic, rate, callback):
        msg = {
            'op' : 'subscribe',
            'topic' : topic,
            'throttle_rate': rate
        }
        self.send(json.dumps(msg))
        self.callbacks[topic] = callback;

    def opened(self):
        print("Connection opened...")

    def advertise_topic(self):
        msg = {
            'op': 'advertise', 
            'topic': '/move_base_simple/goal',
            'type': 'geometry_msgs/PoseStamped'
        }
        self.send(json.dumps(msg))

    def closed(self, code, reason=None):
        print(str(code) + "," + str(reason))

    def received_message(self, m):
        # Send message to callback
        data = m.data.decode("utf-8")
        data_obj = json.loads(data, object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))
        
        if (hasattr(data_obj, 'topic')):        
            callback = self.callbacks[data_obj.topic]
            if callback is not None:
                callback(data_obj)

        if (hasattr(data_obj, 'service') and hasattr(data_obj, 'id')):
            callback = self.serviceCallbacks[data_obj.id]
            del self.serviceCallbacks[data_obj.id]
            if callback is not None:
                callback(data_obj)  
            

    def callService(self, service, args, callback):
        uid = str(uuid.uuid4())[:8]
        self.serviceCallbacks[uid] = callback
        msg = {
            'op': 'call_service',
            'id': uid,
            'service': service,
            'args': args
        }
        self.send(json.dumps(msg))
