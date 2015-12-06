# -*- coding: utf-8 -*-
"""
Tools common to all ZMQ services.
"""
import six

from ..api import APISetting
from ..exc import DispatcherError

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
         

def check_message_part(part):
    """Check the message part."""
    part = six.text_type(part)
    if ":" in part:
        raise ValueError("Message parts can't contain the delimiter ':', got {0:s}".format(part))
    return part

class ZMQCauldronErrorResponse(Exception):
    """A container for ZMQ Cauldron error responses."""
    def __init__(self, message):
        """docstring for __init__"""
        self.message = message
        
    @property
    def response(self):
        """The response data."""
        return self.message
        
class ZMQCauldronParserError(Exception):
    """An error caused by a failed parser."""
    pass
    
    @property
    def response(self):
        """Return response data when parsing failed."""
        return map(six.binary_type, ["\x01", "\x01", "\x01", "ERR", "error", str(self)])

class ZMQCauldronMessage(object):
    """A message object."""
    def __init__(self, command, service, keyword=None, payload=None, direction="REQ"):
        super(ZMQCauldronMessage, self).__init__()
        self.command = check_message_part(command)
        self.service = service
        self.keyword = keyword
        self.payload = check_message_part(payload)
        self.direction = check_message_part(direction)
    
    @property
    def keyword_name(self):
        """The keyword name associated with this message."""
        return "\x01" if self.keyword is None else self.keyword.name
        
    @property
    def service_name(self):
        """The service name associated with this message."""
        return "\x01" if self.service is None else self.service.name
        
    @property
    def dispatcher_name(self):
        """The dispatcher name associated with this message."""
        if self.service is not None and hasattr(self.service, 'dispatcher'):
            return self.service.dispatcher
        else:
            return "\x01"
            
    @property
    def _message_parts(self):
        """Message parts."""
        return [self.service_name, self.dispatcher_name, self.keyword_name, self.direction, self.command, self.payload]
        
    @property
    def data(self):
        """The full message."""
        return map(six.binary_type, self._message_parts)
        
    def response(self, payload):
        """Compose a response."""
        return self.__class__(
            command = self.command,
            service = self.service,
            keyword = self.keyword,
            payload = payload,
            direction = "REP")
            
    def error_response(self, payload):
        """Compose an error response message."""
        return self.__class__(
            command = self.command,
            service = self.service,
            keyword = self.keyword,
            payload = payload,
            direction = "ERR")
            
    def raise_error_response(self, payload):
        """Raise an error response"""
        message = self.error_response(payload)
        raise ZMQCauldronErrorResponse(message)
        
    def to_string(self):
        """Compose a string."""
        return "|".join(self._message_parts)
    
    def __str__(self):
        """String types in python3"""
        return self.to_string()
    if six.PY2:
        def __unicode__(self):
            """Unicode types in python2"""
            return self.to_string()
    
    @classmethod
    def parse(cls, data, service):
        """Parse data. Errors are rasied """
        try:
            service_name, dispatcher_name, keyword_name, direction, command, payload = data
        except ValueError as e:
            raise ZMQCauldronParserError("Can't parse message '{0}' because {1}".format(data, str(e)))
        if service_name == "\x01":
            service = None
            if keyword_name != "\x01":
                raise ZMQCauldronParserError("Can't parse message '{0}' because essage can't specify a keyword with no service.".format(data))
            keyword = None
        elif service_name != service.name:
            raise DispatcherError("Message was sent to the wrong service!")
        if dispatcher_name != "\x01":
            if hasattr(service, 'dispatcher') and dispatcher_name != service.dispatcher:
                raise DispatcherError("Message was sent to the wrong dispatcher! Sent to {0}, received by {1}".format(
                    dispatcher_name, service.dispatcher
                ))
        
        if keyword_name != "\x01":
            keyword = service[keyword_name]
        else:
            keyword = None
        return cls(command, service, keyword, payload, direction)
    

def teardown():
    """Destroy the ZMQ context."""
    try:
        import zmq
    except ImportError:
        pass
    else:
        zmq.Context.instance().destroy()
    