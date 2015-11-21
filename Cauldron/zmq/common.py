# -*- coding: utf-8 -*-
"""
Tools common to all ZMQ services.
"""
import six

from ..api import _Setting

ZMQ_AVAILALBE = _Setting("ZMQ_AVAILALBE", False)
try:
    import zmq
except ImportError:
    ZMQ_AVAILALBE.off()
else:
    ZMQ_AVAILALBE.on()

def check_zmq():
    """Check if ZMQ is available."""
    if ZMQ_AVAILALBE:
        return zmq
    raise RuntimeError("Must have 'zmq' installed to use the zmq backend.")

def zmq_dispatcher_host(config):
    """docstring for zmq_dispatcher_host"""
    return config.get("zmq", "host")
    
def zmq_dispatcher_address(config, bind=False):
    """Return the full dispatcher address."""
    return "{0}://{1}:{2}".format(config.get("zmq", "protocol"), 
        "*" if bind else zmq_dispatcher_host(config), 
        config.get("zmq", "dispatch-port"))
    
def zmq_broadcaster_address(config, bind=False):
    """Return the full broadcaster address."""
    return "{0}://{1}:{2}".format(config.get("zmq", "protocol"),
         "*" if bind else zmq_dispatcher_host(config), 
         config.get("zmq", "broadcast-port"))
         

def compile_message(cmd, service, keyword, value):
    """Compile a message"""
    parts = []
    for part in [cmd, service, keyword]:
        part = six.text_type(part)
        if ":" in part:
            raise ValueError("Command message parts must not contain ':', got '{0:s}'".format(part))
        parts.append(part)
    parts.append(six.text_type(value))
    return "{0:s}:{1:s}:{2:s}:{3:s}".format(*parts)
    
def parse_message(message):
    """Parse a message."""
    cmd, service, keyword, response = message.split(":",3)
    return {'cmd' : cmd, 'service' : service, 'keyword' : keyword, 'response' : response, 'error' : "Error" in cmd }
    
def sync_command(socket, cmd, service, keyword="", value=""):
    """Synchronous command."""
    socket.send(compile_message(cmd, service, keyword, value))
    msg = parse_message(socket.recv())
    if msg['error']:
        raise DispatcherError(msg['response'])
    return msg
    
def teardown():
    """Destroy the ZMQ context."""
    try:
        import zmq
    except ImportError:
        pass
    else:
        zmq.Context.instance().destroy()
    