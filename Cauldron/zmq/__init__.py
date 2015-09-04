# -*- coding: utf-8 -*-
"""
ZeroMQ is a networking protocol with socket-like objects
for writing highly distributed apps. Here, it is used to
implement the request-reply pattern for keyword passing
interfaces, including error handling responses.

"""

DISPATCHER_PORT = 6000
BROADCAST_PORT = 6001

ZMQ_DISPATCHER_BIND = 'tcp://*:{0}'.format(DISPATCHER_PORT)
ZMQ_DISPATCHER_BROADCAST = 'tcp://*:{0}'.format(BROADCAST_PORT)
ZMQ_DISPATCHER_HOST = None

def set_zmq_dispatcher_host(host):
    """Set the ZMQ dispatcher hostname."""
    global ZMQ_DISPATCHER_HOST
    ZMQ_DISPATCHER_HOST = host

def zmq_dispatcher_host():
    """docstring for zmq_dispatcher_host"""
    global ZMQ_DISPATCHER_HOST
    return ZMQ_DISPATCHER_HOST
    
def zmq_dispatcher_address():
    """Return the full dispatcher address."""
    return "tcp://{0}:{1}".format(zmq_dispatcher_host(), DISPATCHER_PORT)
    
def zmq_broadcaster_address():
    """Return the full broadcaster address."""
    return "tcp://{0}:{1}".format(zmq_dispatcher_host(), BROADCAST_PORT)