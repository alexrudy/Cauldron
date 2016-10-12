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

def zmq_get_bind(config, name, group='zmq'):
    """Get a bind address from a configuration"""
    import socket
    url = config.get(group, name)
    if url.startswith("tcp://"):
        parts = list(url.split(":"))
        host = parts[1][2:]
        if host == "localhost":
            parts[1] = "//" + socket.gethostbyname(host)
        else:
            parts[1] = "//*"
        url = ":".join(parts)
    return url

def zmq_get_address(config, name, bind=False, group="zmq"):
    """Construct a ZMQ address."""
    if bind:
        return zmq_get_bind(config, name, group=group)
    else:
        return config.get(group, name)

def zmq_check_nonlocal_address(config, name, group="zmq"):
    """Check that a particular zmq address is nonlocal."""
    from six.moves.urllib.parse import urlparse
    url = urlparse(config.get(group, name))
    if url.scheme in ('inproc'):
        return False
    return True
    
        
def zmq_connect_socket(socket, config, name, group="zmq", log=None, label=None, address=None):
    """Connect a ZMQ Cauldron socket."""
    label = label or name
    log = log or logging.getLogger(__name__)
    try:
        address = address or zmq_get_address(config, name, bind=False)
        socket.connect(address)
    except zmq.ZMQError as e:
        log.exception("Service can't connect to {0} address '{1}' because {2}".format(label, address, e))
        raise
    else:
        log.msg("Connected {0} to {1}".format(label, address))
        return socket

def teardown():
    """Destroy the ZMQ context."""
    pass
    