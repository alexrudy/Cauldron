# -*- coding: utf-8 -*-
"""
A simple microservice framework for ZMQ Messaging.
"""

import weakref
import logging
import threading
import six

FRAMEBLANK = "\x01"
FRAMEFAIL = "\x02"

class MessageVerifyError(Exception):
    """Verify the message error."""
    pass

class ZMQCauldronErrorResponse(Exception):
    """A container for ZMQ Cauldron error responses."""
    
    def __init__(self, message):
        self.message = message
        
class ZMQCauldronParserError(ZMQCauldronErrorResponse):
    """An error caused by a failed parser."""
    pass
    
    @classmethod
    def with_message(cls, message):
        """Add a message to a Cauldron Parser error."""
        return cls(ZMQCauldronMessage(command="parser", payload=message, direction="ERR"))

class ZMQCauldronMessage(object):
    """A message object."""
    
    DIRECTIONS = "REQ REP ERR PUB".split()
    
    def __init__(self, command=FRAMEBLANK, service=FRAMEBLANK, dispatcher=FRAMEBLANK, 
        keyword=FRAMEBLANK, payload=FRAMEBLANK, direction="REQ"):
        super(ZMQCauldronMessage, self).__init__()
        self.command = six.text_type(command or FRAMEBLANK)
        self.service = six.text_type(service or FRAMEBLANK)
        self.dispatcher = six.text_type(dispatcher or FRAMEBLANK)
        self.keyword = six.text_type(keyword or FRAMEBLANK)
        self.payload = six.text_type(payload or FRAMEBLANK)
        if direction not in self.DIRECTIONS:
            raise ValueError("Invalid choice of message direction: {0}".format(direction))
        self.direction = six.text_type(direction)
        
    def verify(self, service):
        """Given a service object, verify that it matches this message."""
        if self.service != FRAMEBLANK:
            if self.service != service.name:
                raise MessageVerifyError("Message was sent to the wrong service! Got {0} expected {1}".format(self.service, service.name))
        if self.dispatcher != FRAMEBLANK:
            if hasattr(service, 'dispatcher') and self.dispatcher != service.dispatcher:
                raise MessageVerifyError("Message was sent to the wrong dispatcher! Got {0} expected {1}".format(self.dispatcher, service.dispatcher))
        if self.keyword != FRAMEBLANK:
            keyword = service[self.keyword]
        else:
            keyword = None
        return keyword
    
    @property
    def _message_parts(self):
        """Message parts."""
        return [self.service, self.dispatcher, self.keyword, self.direction, self.command, self.payload]
        
    @property
    def data(self):
        """The full message data, to be sent over a ZMQ Socket.."""
        return map(lambda s : s.encode('utf-8'), map(six.text_type, self._message_parts))
        
    def _copy_args_(self):
        """Return the keyword arguments required to initialize a new copy of this object."""
        return {
            'command' : self.command,
            'service' : self.service,
            'dispatcher' : self.dispatcher,
            'keyword' : self.keyword,
            'payload' : self.payload,
            'direction' : self.direction,
        }
        
    def response(self, payload):
        """Compose a response."""
        kwargs = self._copy_args_()
        kwargs['payload'] = payload
        kwargs['direction'] = "REP"
        return self.__class__(**kwargs)
            
    def error_response(self, payload):
        """Compose an error response message."""
        kwargs = self._copy_args_()
        kwargs['payload'] = payload
        kwargs['direction'] = "ERR"
        return self.__class__(**kwargs)
    
    def raise_error_response(self, payload):
        """Raise an error response"""
        message = self.error_response(payload)
        raise ZMQCauldronErrorResponse(message)
        
    def to_string(self):
        """Compose a string."""
        return "|".join(self._message_parts)
    
    def __str__(self):
        """String types in python3"""
        return str(self.to_string())
    
    if six.PY2:
        def __unicode__(self):
            """Unicode types in python2"""
            return unicode(self.to_string())
    
    @classmethod
    def parse(cls, data, service=None):
        """Parse data. Errors are raised when appropriate."""
        data = [ d.decode('utf-8') for d in data ]
        try:
            service, dispatcher, keyword, direction, command, payload = data
        except ValueError as e:
            raise ZMQCauldronParserError.with_message(
                "Can't parse message '{0}' because {1}".format(data, str(e)))
        
        if service == FRAMEBLANK:
            if keyword != FRAMEBLANK:
                raise ZMQCauldronParserError.with_message(
                    "Can't parse message '{0}' because message can't specify a keyword with no service.".format(data))
            elif dispatcher != FRAMEBLANK:
                raise ZMQCauldronParserError.with_message(
                    "Can't parser message '{0}' because message can't specify a dispatcher with no service.".format(data))
        return cls(command, service, dispatcher, keyword, payload, direction)

class ZMQMicroservice(threading.Thread):
    """A ZMQ Responder tool."""
    
    _error = None
    
    def __init__(self, context, address, name="microservice", timeout=10):
        super(ZMQMicroservice, self).__init__(name=six.text_type(name))
        import zmq
        self.ctx = weakref.proxy(context or zmq.Context.instance())
        self.running = threading.Event()
        self.timeout = float(timeout)
        self.log = logging.getLogger(name)
        self.address = address
        
        
    def handle(self, message):
        """Handle a message, raising an error if appropriate."""
        try:
            self.log.log(5, "Handling |{0!s}|".format(message))
            method_name = "handle_{0:s}".format(message.command)
            if not hasattr(self, method_name):
                message.raise_error_response("Bad command '{0:s}'!".format(message.command))
            response_payload = getattr(self, method_name)(message)
        except ZMQCauldronErrorResponse as e:
            return e.message
        except Exception as e:
            self.log.error("Error handling '{0}': {1!r}".format(message.command, e))
            return message.error_response("{0!r}".format(e))
        else:
            return message.response(response_payload)
            
    def connect(self):
        """Connect to the address and return a socket."""
        import zmq
        socket = self.ctx.socket(zmq.REP)
        try:
            socket.bind(self.address)
        except zmq.ZMQError as e:
            self.log.error("Service can't bind to address '{0}' because {1}".format(address, e))
            self._error = e
            raise
        return socket
            
    def respond(self):
        """Run the responder"""
        import zmq
        try:
            # This is a local variable to ensure that the socket doesn't leak
            # into another thread, because ZMQ sockets aren't thread-safe.
            socket = self.connect()
            
            self.running.set()
            self.log.log(5, "Starting responder loop.")
            while self.running.is_set():
                if socket.poll(timeout=self.timeout):
                    response = self.handle(ZMQCauldronMessage.parse(socket.recv_multipart()))
                    self.log.log(5, "Responds |{0!s}|".format(response))
                    socket.send_multipart(response.data)
                
        except (zmq.ContextTerminated, weakref.ReferenceError, zmq.ZMQError) as e:
            self.log.log(5, "Service shutdown because '{0!r}'.".format(e))
            self._error = e
        else:
            self.log.log(5, "Shutting down the responder cleanly.")
            try:
                socket.setsockopt(zmq.LINGER, 0)
                socket.close()
            except:
                pass
        finally:
            self.running.clear()
        
        
    def run(self):
        """Run the thread."""
        try:
            self.respond()
        finally:
            self.log.log(5, "Respoder thread finished.")
        
    def check_alive(self, timeout=1.0):
        """Check that the thread is actually alive."""
        self.running.wait(timeout)
        if not self.running.is_set():
            msg = "The dispatcher responder thread did not start."
            if self._error is not None:
                msg += " Thread Error: {0}".format(repr(self._thread._error))
            raise DispatcherError(msg)
        
    def stop(self):
        """Stop the responder thread."""
        self.running.clear()
        