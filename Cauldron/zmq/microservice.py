# -*- coding: utf-8 -*-
"""
A simple microservice framework for ZMQ Messaging.
"""

import weakref
import logging
import threading
import six
import binascii
import atexit
import collections
import uuid

from ..exc import DispatcherError

FRAMEBLANK = six.binary_type("\x01")
FRAMEFAIL = six.binary_type("\x02")
FRAMEDELIMITER = six.binary_type("")

class MessageType(object):
    """A message direction object"""
    def __init__(self, origin, responder):
        super(MessageType, self).__init__()
        self._origin = origin
        self._responder = responder
        
    def __contains__(self, key):
        """Does the direction contain a key?"""
        return key in self.codes
        
    @property
    def codes(self):
        """The set of all passable codes."""
        return set([self.forward, self.reply, self.error, self.broadcast])
        
    @property
    def origin(self):
        """Return the origin point."""
        return self.ENDPOINT[self._origin]
    
    @property
    def responder(self):
        """Return the responding point."""
        return self.ENDPOINT[self._responder]
        
    @property
    def forward(self):
        """Forward code."""
        return "{0}{1}{2}".format(self._origin, self._responder, "Q")
        
    @property
    def reply(self):
        """Reply code."""
        return "{0}{1}{2}".format(self._origin, self._responder, "P")
        
    @property
    def error(self):
        """Error code"""
        return "{0}{1}{2}".format(self._origin, self._responder, "E")
        
    @property
    def broadcast(self):
        """Broadcast code."""
        return "{0}{1}{2}".format(self._origin, self._responder, "B")
        
    def path(self, code):
        """Path for a given code."""
        kind = self.KIND[code]
        if code in "QB":
            return (self.origin, self.responder, kind)
        elif code in "PE":
            return (self.responder, self.origin, kind)
    
    KIND = {"Q" : "Query", "P": "Reply", "E": "Error", "B": "Broadcast"}
    ENDPOINT = {"C" : "Client", "S": "Service", "D":"Dispatcher", "B":"Broker"}
        

class Directions(collections.Mapping):
    """A collection of directions."""
    def __init__(self, *args):
        super(Directions, self).__init__()
        self._data = list(*args)
        
    def __getitem__(self, key):
        """Get a direction."""
        for direction in self._data:
            if key in direction:
                return direction
        else:
            raise KeyError("No message direction {0}".format(key))
        
    def __contains__(self, key):
        """Contains a direction?"""
        for direction in self._data:
            if key in direction:
                return True
        else:
            return False
            
    def __iter__(self):
        """Iterate"""
        return iter(self._data)
        
    def __len__(self):
        """Length of the data."""
        return len(self._data)
        
    @property
    def codes(self):
        """Valid message codes"""
        return set([ code for tp in self for code in tp.codes ]) 
    
    def path(self, key):
        """Decode a message option into a path (from, to, kind)."""

        if key[2] == "Q":
            return (endpoints[key[0]], endpoints[key[1]], kinds[key[2]])
        else:
            return (endpoints[key[1]], endpoints[key[0]], kinds[key[2]])
    
    def iserror(self, code):
        """Determine if a code is an error."""
        return code[2] == "E"
        
    def isreply(self, code):
        """Determine if a code is a reply."""
        return code[2] == "P"
    
    def error(self, key):
        """Get the error code."""
        return self[key].error
        
    def reply(self, key):
        """Get the reply code."""
        if key[2] in "QB":
            return self[key].reply
        else:
            return self[key].forward

# This is a set of named tuples.
DIRECTIONS = Directions([
    MessageType("C", "D"),
    MessageType("D", "B"),
    MessageType("C", "B"),
    MessageType("C", "S"),
    MessageType("S", "D"),
])


def _exit_handler(thread_ref):
    """Exit handler"""
    thread = thread_ref()
    if thread is not None:
        thread.stop()
    

class MessageVerifyError(Exception):
    """Verify the message error."""
    pass

class ZMQCauldronErrorResponse(Exception):
    """A container for ZMQ Cauldron error responses."""
    
    def __init__(self, msg, message):
        super(ZMQCauldronErrorResponse, self).__init__(msg)
        self.message = message
        
class ZMQCauldronParserError(ZMQCauldronErrorResponse):
    """An error caused by a failed parser."""
    pass
    
    @classmethod
    def with_message(cls, message):
        """Add a message to a Cauldron Parser error."""
        response = ZMQCauldronMessage(command="parser", payload=message, direction="CDE")
        return cls(message, response)

class ZMQCauldronMessage(object):
    """A message object."""
    
    NPARTS = 7
    
    def __init__(self, command=FRAMEBLANK, service=FRAMEBLANK, dispatcher=FRAMEBLANK, 
        keyword=FRAMEBLANK, payload=FRAMEBLANK, direction="CDQ", prefix=None, identifier=None):
        super(ZMQCauldronMessage, self).__init__()
        self.command = six.text_type(command or FRAMEBLANK)
        self.service = six.text_type(service or FRAMEBLANK)
        self.dispatcher = six.text_type(dispatcher or FRAMEBLANK)
        self.keyword = six.text_type(keyword or FRAMEBLANK)
        self.payload = six.text_type(payload or FRAMEBLANK)
        if direction not in DIRECTIONS.codes:
            raise ValueError("Invalid choice of message direction: {0}".format(direction))
        self.direction = six.text_type(direction)
        self.identifier =  six.binary_type(identifier) if identifier is not None else uuid.uuid4().bytes
        self.prefix = map(six.binary_type, prefix or [])
        
    def _parse_prefix(self):
        """Handle the prefix."""
        self._client_id = None
        self._dispatcher_id = None
        
        _from, _to, _kind = DIRECTIONS[self.direction].path(self.direction[2])
        
        if _from in ("Client", "Service") and len(self.prefix) >= 2:
            self._client_id = self.prefix[0]
        elif _from == "Dispatcher" and len(self.prefix) >= 2:
            self._dispatcher_id = self.prefix[0]
        
        if _to == "Dispatcher" and len(self.prefix) >= 2:
            self._dispatcher_id = self.prefix[-2]
        if _to in ("Client", "Service") and len(self.prefix) >= 2:
            self._client_id = self.prefix[-2]
        
    @property
    def iserror(self):
        """Determine if this message is an error."""
        return DIRECTIONS.iserror(self.direction)
        
    @property
    def isvalid(self):
        """Deterime if this message is not an error and has content."""
        return (not self.iserror) and self.payload not in [FRAMEBLANK, FRAMEFAIL]
        
    @property
    def client_id(self):
        """Return the client ID if it is in the prefix."""
        self._parse_prefix()
        if self._client_id is not None:
            return self._client_id
        else:
            raise ValueError("Prefix doesn't appear to contain the client ID.")
        
    @property
    def dispatcher_id(self):
        """Return the dispatcher ID if it is in the prefix."""
        self._parse_prefix()
        if self._dispatcher_id is not None:
            return self._dispatcher_id
        else:
            raise ValueError("Prefix doesn't appear to contain the dispatcher ID.")
        
    def verify(self, service):
        """Given a service object, verify that it matches this message."""
        if self.service != FRAMEBLANK:
            if self.service != service.name:
                raise MessageVerifyError("Message was sent to the wrong service! Got {0} expected {1}".format(self.service, service.name))
        else:
            self.service = service.name
        
        if self.dispatcher != FRAMEBLANK:
            if hasattr(service, 'dispatcher') and self.dispatcher != service.dispatcher:
                raise MessageVerifyError("Message was sent to the wrong dispatcher! Got {0} expected {1}".format(self.dispatcher, service.dispatcher))
        elif hasattr(service, 'dispatcher'):
            self.dispatcher = service.dispatcher
        
    
    @property
    def _message_parts(self):
        """Message parts."""
        return [self.service, self.dispatcher, self.keyword, self.direction, self.command, self.payload]
        
    @property
    def data(self):
        """The full message data, to be sent over a ZMQ Socket.."""
        return self.prefix + map(lambda s : s.encode('utf-8'), map(six.text_type, self._message_parts)) + [self.identifier]
        
    def __iter__(self):
        """Allow us to send messages directly."""
        return iter(self.data)
        
    def __getitem__(self, key):
        """Allow us to send messages directly."""
        return self.data[key]
        
    def __getstate__(self):
        """Return the keyword arguments required to initialize a new copy of this object."""
        return {
            'command' : self.command,
            'service' : self.service,
            'dispatcher' : self.dispatcher,
            'keyword' : self.keyword,
            'payload' : self.payload,
            'direction' : self.direction,
            'identifier' : self.identifier,
            'prefix': self.prefix,
        }
        
    def copy(self):
        """A copy of this message."""
        return self.__class__(**self.__getstate__())
        
    def response(self, payload):
        """Compose a response."""
        kwargs = self.__getstate__()
        kwargs['payload'] = payload
        kwargs['direction'] = DIRECTIONS.reply(self.direction)
        return self.__class__(**kwargs)
            
    def error_response(self, payload):
        """Compose an error response message."""
        kwargs = self.__getstate__()
        kwargs['payload'] = payload
        kwargs['direction'] = DIRECTIONS.error(self.direction)
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
        return str("|{0}|".format(self.to_string()))
    
    if six.PY2:
        def __unicode__(self):
            """Unicode types in python2"""
            return unicode("|{0}|".format(self.to_string()))
    
    def __repr__(self):
        """Represent the message, including prefix."""
        return "<{0} |{1}|{2}>".format(self.__class__.__name__,
            "|".join(map(binascii.hexlify, self.prefix)), self.to_string())
    
    @classmethod
    def parse(cls, data):
        """Parse data. Errors are raised when appropriate."""
        
        if len(data) > cls.NPARTS:
            prefix = data[:-cls.NPARTS]
            data = data[-cls.NPARTS:]
        else:
            prefix = None
        try:
            service, dispatcher, keyword, direction, command, payload, identifier = data
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
        return cls(command, service, dispatcher, keyword, payload, direction, prefix, identifier)

class ZMQMicroservice(threading.Thread):
    """A ZMQ Responder tool."""
    
    _error = None
    
    def __init__(self, context, address, name="microservice", use_broker=False, timeout=5):
        super(ZMQMicroservice, self).__init__(name=six.text_type(name))
        import zmq
        self.ctx = weakref.proxy(context or zmq.Context.instance())
        self.running = threading.Event()
        self.timeout = float(timeout)
        self.log = logging.getLogger(name)
        self.address = address
        self.use_broker = bool(use_broker)
        
        
    def handle(self, message):
        """Handle a message, raising an error if appropriate."""
        try:
            method_name = "handle_{0:s}".format(message.command)
            if not hasattr(self, method_name):
                message.raise_error_response("Bad command '{0:s}'!".format(message.command))
            response_payload = getattr(self, method_name)(message)
        except ZMQCauldronErrorResponse as e:
            self.log.log(5, "{0!r}.send({1!r})".format(self, e.message))
            return e.message
        except Exception as e:
            self.log.error("Error handling '{0}': {1!r}".format(message.command, e))
            return message.error_response("{0!r}".format(e))
        else:
            response = message.response(response_payload)
            self.log.log(5, "{0!r}.send({1!r})".format(self, response))
            return response
            
    def connect(self):
        """Connect to the address and return a socket."""
        import zmq
        if self.use_broker:
            socket = self.ctx.socket(zmq.REQ)
        else:
            socket = self.ctx.socket(zmq.REP)
        
        signal = self.ctx.socket(zmq.PAIR)
        signal.bind("inproc://{0:s}".format(hex(id(self))))
        try:
            if self.use_broker:
                socket.connect(self.address)
            else:
                socket.bind(self.address)
        except zmq.ZMQError as e:
            self.log.error("Service can't bind to address '{0}' because {1}".format(self.address, e))
            self._error = e
            raise
        else:
            self.log.debug("Microservice {0} connected to address '{1}'".format(self.name, self.address))
            
        if self.use_broker:
            # Ready sentinel for broker.
            self.greet_broker(socket, signal)
        return socket, signal
        
    def greet_broker(self, socket, signal):
        """Send the appropriate greeting to the broker."""
        socket.send_multipart([FRAMEBLANK] + ZMQCauldronMessage(command="ready").data)
        self.log.log(5, "Sent broker a welcome message.")
            
    def respond(self):
        """Run the responder"""
        import zmq
        try:
            # This is a local variable to ensure that the socket doesn't leak
            # into another thread, because ZMQ sockets aren't thread-safe.
            socket, signal = self.connect()
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            poller.register(signal, zmq.POLLIN)
            
            self.running.set()
            self.log.log(5, "Starting responder loop.")
            while self.running.is_set():
                ready = dict(poller.poll(timeout=self.timeout*1e3))
                if ready.get(socket) == zmq.POLLIN:
                    response = self.handle(ZMQCauldronMessage.parse(socket.recv_multipart()))
                    self.log.log(5, "Responds {0!r}".format(response))
                    socket.send_multipart(response.data)
                
        except (zmq.ContextTerminated, weakref.ReferenceError, zmq.ZMQError) as e:
            self.log.log(5, "Service shutdown because '{0!r}'.".format(e))
            self._error = e
        except Exception as e:
            self._error = e
            self.log.log(5, "Service shutdown because '{0!r}'.".format(e))
            raise
        else:
            self.log.log(5, "Shutting down the responder cleanly.")
            try:
                ready = dict(poller.poll(timeout=self.timeout*1e3))
                if ready.get(signal) == zmq.POLLIN:
                    signal.recv()
                signal.close(linger=0)
                socket.close(linger=0)
            except:
                pass
        finally:
            self.log.log(5, "Stopped responder loop.")
            self.running.clear()
        
        
    def run(self):
        """Run the thread."""
        atexit.register(_exit_handler, weakref.ref(self))
        try:
            self.respond()
        finally:
            self.log.log(5, "Respoder thread finished.")
        
    def check_alive(self, timeout=1.0):
        """Check that the thread is actually alive."""
        self.running.wait(timeout)
        if not self.running.is_set():
            msg = "The dispatcher responder thread is not alive."
            if self._error is not None:
                msg += " Thread Error: {0}".format(repr(self._error))
            else:
                msg += " No error was reported."
            raise DispatcherError(msg)
        
    def stop(self):
        """Stop the responder thread."""
        import zmq
        if not self.isAlive():
            return
        
        if self.running.is_set() and (not self.ctx.closed):
            self.running.clear()
            signal = self.ctx.socket(zmq.PAIR)
            signal.connect("inproc://{0:s}".format(hex(id(self))))
            signal.send("", flags=zmq.NOBLOCK)
            signal.close(linger=0)
        self.running.clear()
        self.join()
        self.log.debug("Joined microservice {0}".format(self.name))
        
        