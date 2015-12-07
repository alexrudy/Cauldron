# -*- coding: utf-8 -*-
"""
Tools common to all ZMQ services.
"""
import six

from ..api import APISetting
from ..exc import DispatcherError, WrongDispatcher

ZMQ_AVAILABLE = APISetting("ZMQ_AVAILABLE", False)
try:
    import zmq
except ImportError:
    ZMQ_AVAILABLE.off()
else:
    ZMQ_AVAILABLE.on()
    
__all__ = ['ZMQ_AVAILABLE', 'check_zmq']

def check_zmq():
    """Check if ZMQ is available."""
    if ZMQ_AVAILABLE:
        return zmq
    raise RuntimeError("Must have 'zmq' installed to use the zmq backend.")

def zmq_router_address(config, bind=False):
    """Return the ZMQ router host address."""
    return "{0}://{1}:{2}".format(config.get("zmq-router", "protocol"), 
        "*" if bind else zmq_router_host(config), 
        config.get("zmq-router", "port"))

def zmq_router_host(config):
    """Return the ZMQ router host."""
    return config.get("zmq-router", "host")
    

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
    

def teardown():
    """Destroy the ZMQ context."""
    try:
        import zmq
    except ImportError:
        pass
    else:
        zmq.Context.instance().destroy()
    