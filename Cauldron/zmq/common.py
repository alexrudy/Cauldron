# -*- coding: utf-8 -*-
"""
Tools common to all ZMQ services.
"""
import six

from ..api import _Setting
from ..exc import DispatcherError

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
        return str(self.message)
        
class ZMQCauldronParserError(Exception):
    """An error caused by a failed parser."""
    pass
    
    @property
    def response(self):
        """Return response data when parsing failed."""
        return ":".join(["", "", "ERR", "", str(self)])

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
        return "" if self.keyword is None else self.keyword.name
        
    @property
    def service_name(self):
        """The service name associated with this message."""
        return "" if self.service is None else self.service.name
        
        
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
        return ":".join(map(check_message_part,[self.service_name, self.keyword_name, self.direction, self.command, self.payload]))
    
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
            service_name, keyword_name, direction, command, payload = data.split(":",4)
        except ValueError as e:
            raise ZMQCauldronParserError("Can't parse message '{0}' because {1}".format(data, str(e)))
        if service_name == "":
            service = None
            if keyword_name != "":
                raise ZMQCauldronParserError("Can't parse message '{0}' because essage can't specify a keyword with no service.".format(data))
            keyword = None
        elif service_name != service.name:
            raise DispatcherError("Message was sent to the wrong dispatcher!")
        else:
            if keyword_name is not "":
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
    