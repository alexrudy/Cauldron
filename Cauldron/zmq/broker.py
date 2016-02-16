# -*- coding: utf-8 -*-
"""
A single message broker service to distribute messages between clients and dispatchers.
"""
from __future__ import absolute_import

import threading
import time
import logging
import collections
import binascii
import weakref

from ..config import read_configuration
from .microservice import ZMQCauldronMessage, ZMQCauldronErrorResponse, FRAMEBLANK, FRAMEFAIL, DIRECTIONS
from .common import zmq_address
from ..exc import DispatcherError

__all__ = ['ZMQBroker', 'NoResponseNecessary', 'NoDispatcherAvailable', 'MultipleDispatchersFound']

def logger_getChild(logger, child):
    """Get a child logger of a parent."""
    name = "{0}.{1}".format(logger.name, child)
    return logging.getLogger(name)

class NoResponseNecessary(Exception):
    """NoResponseNecessary"""
    pass

class NoDispatcherAvailable(DispatcherError):
    """Raised when no dispatcher is available."""
    pass
    
class MultipleDispatchersFound(DispatcherError):
    """Raised when too many dispatchers are identified for a keyword."""
    pass
    
class FanMessage(object):
    """An identification message request"""
    def __init__(self, service, client, message, timeout=10.0):
        super(FanMessage, self).__init__()
        self.message = message # The original message.
        self.service = service # The parent service.
        self.client = client # The original identifier.
        
        self.id = message.identifier # A human-readable binary identifier.
        self.timeout = time.time() + timeout
        # Store the results.
        self.pending = set()
        self.responses = dict()
        self.valid = False # Did we message at least one dispatcher?
        
        
    def __repr__(self):
        """A message representation."""
        return "<FanMessage {0:s} pending={1:d} lifetime={2:.0f} responses={3:d}>".format(
            binascii.hexlify(self.id), len(self.pending), self.timeout - time.time(), len(self.responses)
        )
        
    @property
    def done(self):
        """Is this fan complete?"""
        return (not len(self.pending)) or (time.time() > self.timeout)
        
    def generate_message(self, dispatcher):
        """Generate a message for a specific dispatcher."""
        message = self.message.copy()
        message.direction = "SDQ"
        self.pending.add(dispatcher.id)
        self.valid = True
        message.prefix = [self.client.id, b""]
        return message
        
    def add(self, dispatcher, message):
        """Add item to the fan message."""
        self.client.log.log(5, "{0!r}.add({1!r})".format(self, message))
        if message.payload not in (FRAMEBLANK, FRAMEFAIL) and not DIRECTIONS.iserror(message.direction):
            self.responses[dispatcher.name] = message.payload
        self.pending.remove(dispatcher.id)
        
    def resolve(self):
        """Fan message responses."""
        self.client.log.log(5, "{0!r}.resolve()".format(self))
        if not self.valid:
            response = self.message.error_response("No dispatchers for '{0}'".format(self.message.service))
            return response
        elif len(self.responses) == 1:
            response = self.message.response(self.responses.values()[0])
            response.dispatcher = self.responses.keys()[0]
            return response
        elif len(self.responses):
            return self.message.response(":".join(self.responses.values()))
        else:
            return self.message.response(FRAMEFAIL)
        
    def send(self, socket):
        """Send the final response"""
        response = self.resolve()
        self.service.scrape(response)
        self.client.send(response, socket)
        

class MessageReciept(object):
    """A simple message receipt object."""
    
    __slots__ = ('message', 'sent')
    
    def __init__(self, message):
        super(MessageReciept, self).__init__()
        self.message = message
        self.sent = time.time()

class Lifetime(object):
    """An object with a lifetime"""
    
    def __init__(self, service):
        super(Lifetime, self).__init__()
        self.service = weakref.proxy(service)
        self._message_pool = dict()
        self.beat()
        
    def beat(self):
        """Mark a heartbeat"""
        self._expiration = time.time() + self.service.broker.timeout
        
    @property
    def alive(self):
        """Is this object alive?"""
        return time.time() < (self._expiration + 4 * self.service.broker.timeout)
        
    @property
    def shouldbeat(self):
        """Should this thing ask for a heartbeat."""
        return time.time() > self._expiration
        
    @property
    def lifetime(self):
        """Return the lifetime of this object."""
        return (self._expiration + 4 * self.service.broker.timeout) - time.time()
        
    @property
    def active(self):
        """Is this object active?"""
        return len(self._message_pool)
        
    def activate(self, message):
        """Base-class method to record a message as sent."""
        self._message_pool[message.identifier] = MessageReciept(message)
    
    def deactivate(self, message):
        """Record a message reciept. Generally means the source was alive!"""
        value = self._message_pool.pop(message.identifier, None)
        self.beat()
        return value
        
    def expire(self):
        """Expire, by returning a list of messages to deactivate."""
        while len(self._message_pool):
            yield self._message_pool.pop(self._message_pool.keys()[0])
            
    def clear(self):
        """Clear the message pool"""
        self._message_pool.clear()
    
    def __repr__(self):
        return "<{0} name='{1}' lifetime={2:.0f} open={3:d}>".format(self.__class__.__name__, self.name, self.lifetime, self.active)

class Client(Lifetime):
    """A simple representation of a client connection."""
    def __init__(self, client_id, service):
        super(Client, self).__init__(service)
        self.id = client_id
        self.name = binascii.hexlify(self.id)
        self.log = logger_getChild(service.log, "Client.{0}".format(binascii.hexlify(self.id)))
    
    def send(self, message, socket):
        """Send a message to this client."""
        message.prefix = [self.id, b""]
        socket.send_multipart(message.data)
        self.log.log(5, "{0!r}.send({1!r})".format(self, message))
        self.deactivate(message)
        

class Dispatcher(Lifetime):
    """A simple representation of a dispatcher."""
    def __init__(self, name, dispatcher_id, service):
        super(Dispatcher, self).__init__(service)
        self.id = dispatcher_id
        self.name = name
        self.service = weakref.proxy(service)
        self.log = logger_getChild(self.service.log,self.name)
        self.message = None
        self.keywords = dict()
        
    def send(self, message, socket):
        """Send a message to this dispatcher."""
        message.prefix = [self.id, b""] + message.prefix
        socket.send_multipart(message.data)
        self.log.log(5, "{0!r}.send({1!r})".format(self, message))
        self.activate(message)
        


handlers = {}

def handler(code):
    """Mark a new handler."""
    def _(func):
        """Decorator with bound arguments."""
        handlers[code] = func.__name__
        return func
    return _

class Service(object):
    """A simple representation of a service"""
    
    def __init__(self, name, broker):
        super(Service, self).__init__()
        self.name = name.upper()
        self.keywords = {}
        self.dispatchers = {}
        self.clients = {}
        self.broker = weakref.proxy(broker)
        self.log = logger_getChild(self.broker.log, "Service.{0}".format(self.name))
        self._fans = {}
        
    def __repr__(self):
        """Represent this object."""
        return "<{0} name={1} dispatchers={2:d} clients={3:d}>".format(self.__class__.__name__, self.name, len(self.dispatchers), len(self.clients))
        
    def get_dispatcher(self, message, recv=True):
        """Get a dispatcher object from a message."""
        try:
            dispatcher_object = self.dispatchers[message.dispatcher]
            if dispatcher_object.id != message.dispatcher_id:
                dispatcher_object.clear()
                dispatcher_object.id = message.dispatcher_id
                
        except KeyError:
            try:
                dispatcher_object = self.dispatchers[message.dispatcher] = Dispatcher(message.dispatcher, message.dispatcher_id, self)
            except ValueError:
                raise DispatcherError("No dispatcher available for {0}".format(message.dispatcher))
        if recv:
            self.log.log(5, "{0!r}.recv({1!r})".format(dispatcher_object, message))
            dispatcher_object.deactivate(message)
        return dispatcher_object
        
    def get_client(self, message, recv=True):
        """Retrieve a client object by client ID."""
        try:
            client_object = self.clients[message.client_id]
        except KeyError:
            client_object = self.clients[message.client_id] = Client(message.client_id, self)
        if recv:
            self.log.log(5, "{0!r}.recv({1!r})".format(client_object, message))
        return client_object
        
    def scrape(self, message):
        """Scrape a message for dispatcher information."""
        # Cache dispatcher identities for easy lookup later.
        if message.dispatcher != FRAMEBLANK:
            if message.isvalid:
                # If this message can identify the disptacher, save it for later.
                self.keywords[message.keyword.upper()] = message.dispatcher
            if message.command == "identify" and message.isvalid:
                self.dispatchers[message.dispatcher].keywords[message.keyword.upper()] = message.payload
            
    
    def paste(self, message):
        """Opposite of scrape, paste the dispatcher back into the message."""
        if message.dispatcher == FRAMEBLANK:
            # Locate the correct dispatcher.
            if message.keyword != FRAMEBLANK:
                try:
                    dispatcher_name = self.keywords[message.keyword.upper()]
                    dispatcher = self.dispatchers[dispatcher_name]
                except KeyError:
                    raise NoDispatcherAvailable("No dispatcher is available for '{0}'".format(message.service))
                message.dispatcher = dispatcher.name
            else:
                raise DispatcherError("Ambiguous dispatcher specification in message {0!s}".format(message))
                
        try:
            return self.dispatchers[message.dispatcher]
        except KeyError:
            raise NoDispatcherAvailable("Dispatcher '{0}' is not available for '{1}'".format(message.dispatcher, message.service))
        
    
    def finish_fan_messages(self, socket):
        """Finish a fan message"""
        for fmessage in list(self._fans.values()):
            if fmessage.done:
                del self._fans[fmessage.id]
                fmessage.send(socket)
        
    def expire(self, socket):
        """Expire messages."""
        for name in self.dispatchers.keys():
            dispatcher = self.dispatchers[name]
            if dispatcher.alive:
                continue
            self.log.debug("{0!r} expiring".format(dispatcher))
            for reciept in dispatcher.expire():
                response = reciept.message.error_response("Dispatcher Timed Out")
                self.handle(response, socket)
            del self.dispatchers[name]
        
    def beat(self, socket):
        """Start heartbeat messages where necssary."""
        for name in self.dispatchers.keys():
            dispatcher = self.dispatchers[name]
            if not dispatcher.shouldbeat:
                continue
            if dispatcher.message is not None:
                msg = dispatcher.message.response("beat")
                msg.command = "heartbeat"
                dispatcher.send(msg, socket)
        
    def handle(self, message, socket):
        """Handle"""
        try:
            method = getattr(self, handlers[message.direction])
            # self.log.log(5, "{0!r}.handle({1!r})".format(self, message))
            method(message, socket)
        except Exception as e:
            self.log.exception("Handling exception {0}".format(e))
            socket.send_multipart(message.error_response(repr(e)))
        else:
            self.finish_fan_messages(socket)
            
        
    @handler("DBE")
    def handle_dispatcher_broker_error(self, message, socket):
        """This is an unusual case which can happen during cleanup."""
        self.log.log(5, "Discarding {0!r}".format(message))
        
    @handler("DBQ")
    def handle_dispatcher_broker_query(self, message, socket):
        """Handle a query from a dispatcher to a broker."""
        dispatcher = self.get_dispatcher(message)
        if message.command == "welcome":
            message.prefix = []
            dispatcher.send(message.response("confirmed"), socket)
        elif message.command == "ready":
            dispatcher.message = message
            self.log.info("{0!r} is ready.".format(dispatcher))
        elif message.command == "heartbeat":
            self.log.info("{0!r} is alive.".format(dispatcher))
            
        else:
            dispatcher.send(message.error_response("unknown command"), socket)
        
    @handler("SDE")
    @handler("SDP")
    def handle_service_dispathcer_reply(self, message, socket):
        """Handle a dispatcher fan-out response.
        
        | Dispatcher -> Broker | --> Client
        
        """
        dispatcher = self.get_dispatcher(message)
        client = self.get_client(message, recv=False)
        self._fans[message.identifier].add(dispatcher, message)
        
    @handler("CSQ")
    def handle_client_service_query(self, message, socket):
        """Handle the start of a fan message.
        
        | Dispatcher <- Broker <- Client |
        
        """
        client = self.get_client(message)
        client.activate(message)
        
        try:
            if message.command == "identify":
                dispatcher_name = self.keywords[message.keyword.upper()]
                dispatcher = self.dispatchers[dispatcher_name]
                ktl_type = dispatcher.keywords[message.keyword.upper()]
            else:
                raise KeyError
        except KeyError:
            fmessage = FanMessage(self, client, message)
            self.log.log(5, "{0!r}.start({1!r})".format(fmessage, message))
        
            self._fans[fmessage.id] = fmessage
        
            for dispatcher in self.dispatchers.values():
                dispatcher.send(fmessage.generate_message(dispatcher), socket)
        else:
            response = message.response(ktl_type)
            response.dispatcher = dispatcher_name
            client.send(response, socket)
        
    @handler("CDE")
    @handler("CDP")
    def handle_client_dispathcer_reply(self, message, socket):
        """Handle dispatcher reply
        
        | Dispatcher -> Broker -> Client |
        
        """
        client = self.get_client(message, recv=False)
        dispatcher = self.get_dispatcher(message)
        
        self.scrape(message)
        client.send(message, socket)
        
    @handler("CDQ")
    def handle_client_dispatcher_query(self, message, socket):
        """Handle a dispathcer request.
        
        | Dispatcher <- Broker <- Client |
        
        """
        client = self.get_client(message)
        client.activate(message)
        try:
            dispatcher = self.paste(message)
            dispatcher.send(message, socket)
        except DispatcherError as e:
            client.send(message.error_response(e), socket)
        
    @handler("CBQ")
    def handle_client_broker_query(self, message, socket):
        """Handle the client asking the broker for something."""
        client = self.get_client(message)
        client.activate(message)
        if message.command == "lookup":
            # The client has asked for the subscription address, we should send that to them.
            response = message.response(self.broker._pub_address)
        elif message.command == "locate":
            # The client has asked us if a service is locatable.
            response = message.response("yes" if len(self.dispatchers) else "no")
        else:
            response = message.error_response("unknown command")
        
        client.send(response, socket)



class ZMQBroker(threading.Thread):
    """A broker object for handling ZMQ Messaging patterns"""
    def __init__(self, name, address, pub_address, sub_address, context=None, timeout=1.0):
        super(ZMQBroker, self).__init__(name=name)
        import zmq
        self.context = context or zmq.Context.instance()
        self.running = threading.Event()
        self.log = logging.getLogger("DFW.Broker." + name )
        self._address = address
        self._pub_address = pub_address
        self._sub_address = sub_address
        self.timeout = float(timeout)
        self._local = threading.local()
        
        self.services = dict()
        
    @classmethod
    def from_config(cls, config, name="ConfiguredBroker"):
        """Make a new item from a configuration."""
        config = read_configuration(config)
        address = zmq_address(config, "broker", bind=True)
        sub_address = zmq_address(config, "publish", bind=True)
        pub_address = zmq_address(config, "broadcast", bind=True)
        timeout = config.get("zmq", "timeout")
        return cls(name, address, pub_address, sub_address, timeout=timeout)
        
    @classmethod
    def serve(cls, config, name="ServerBroker"):
        """Make a broker which serves."""
        obj = cls.from_config(config, name)
        obj.run()
        return obj
        
    @classmethod
    def daemon(cls, config=None, daemon=True):
        """Serve in a process."""
        import multiprocessing as mp
        proc = mp.Process(target=cls.serve, args=(config,), name="ZMQBroker")
        proc.daemon = daemon
        proc.start()
        return proc
    
    @classmethod
    def thread(cls, config=None, daemon=True):
        """Serve in a thread."""
        obj = cls.from_config(config)
        obj.daemon = daemon
        obj.start()
        return obj
    
        
    def connect(self, address, mode="ROUTER"):
        """Connect the frontend and backend sockets."""
        import zmq
        socket = self.context.socket(getattr(zmq, mode))
        try:
            socket.bind(address)
        except zmq.ZMQError as e:
            self.log.error("Can't bind to address '{0}' because {1}".format(address, e))
            self._error = e
            raise
        else:
            self.log.debug("Broker bound {0} to address '{1}'".format(mode, address))
        return socket
        
    def get_service(self, service):
        """Try to get a service."""
        try:
            service_object = self.services[service.upper()]
        except KeyError:
            service_object = self.services[service.upper()] = Service(service, self)
            self.log.debug("Registered new service '{0}'".format(service))
        return service_object
            
    def cleanup(self, socket):
        """docstring for cleanup"""
        for service in self.services.values():
            service.finish_fan_messages(socket)
            service.expire(socket)
            service.beat(socket)
    
    def prepare(self):
        """Thread local way to prepare connections."""
        import zmq
        socket = self._local.socket = self.connect(self._address)
        xpub = self._local.xpub = self.connect(self._pub_address, 'XPUB')
        xsub = self._local.xsub = self.connect(self._sub_address, 'XSUB')
        signal = self._local.signal = self.connect("inproc://{0}".format(hex(id(self))), "PAIR")
        self._local.poller = zmq.Poller()
        self._local.poller.register(socket, zmq.POLLIN)
        self._local.poller.register(xsub, zmq.POLLIN)
        self._local.poller.register(xpub, zmq.POLLIN)
        self._local.poller.register(signal, zmq.POLLIN)
    
    def close(self):
        """Close thread-local sockets."""
        import zmq
        if not hasattr(self._local, 'socket'):
            return
        
        self._local.socket.close(linger=0)
        self._local.xpub.close(linger=0)
        self._local.xsub.close(linger=0)
        
        signal = self._local.signal
        if signal.closed:
            pass
        elif signal.poll(timeout=1):
            signal.recv()
        signal.close(linger=0)
        del self._local.socket, self._local.xpub, self._local.xsub, self._local.signal
        
    
    def respond(self):
        """Respond to a single message on each socket."""
        import zmq
        poller = self._local.poller
        socket = self._local.socket
        xpub = self._local.xpub
        xsub = self._local.xsub
        signal = self._local.signal
        
        try:
            sockets = dict(poller.poll(timeout=self.timeout * 1e3))
            
            if sockets.get(signal) == zmq.POLLIN:
                self.running.clear()
                return
            
            if sockets.get(socket) == zmq.POLLIN:
                request = socket.recv_multipart()
                if len(request) > 3:
                    message = ZMQCauldronMessage.parse(request)
                    service = self.get_service(message.service)
                    service.handle(message, socket)
                else:
                    self.log.log(5, "Malofrmed request: |{0}|".format("|".join(map(binascii.hexlify,request))))
        
            self.cleanup(socket)
        
            if sockets.get(xsub) == zmq.POLLIN:
                request = xsub.recv_multipart()
                xpub.send_multipart(request)
            if sockets.get(xpub) == zmq.POLLIN:
                request = xpub.recv_multipart()
                xsub.send_multipart(request)
            
        
        except zmq.ZMQError as e:
            self.running.clear()
        
    
    def stop(self):
        """Stop the responder."""
        import zmq
        
        if not self.context.closed:
            signal = self.context.socket(zmq.PAIR)
        
            signal.connect("inproc://{0:s}".format(hex(id(self))))
            self.running.clear()
            signal.send("")
            signal.close(linger=0)
        else:
            self.running.clear()
        self.join()
        self.close()

    def run(self):
        """Run method for threads."""
        self.prepare()
        
        self.running.set()
        self.log.debug("Broker running. Timeout={0}".format(self.timeout))
        while self.running.is_set():
            self.respond()
            
        self.close()
        self.log.debug("Broker done.")
        
    

def _setup_logging(verbose):
    """Try to use lumberjack to enable logging when in a subprocess."""
    try:
        import lumberjack
        lumberjack.setup_logging("DFW.Broker", mode='stream', level=30 - 10 * verbose)
        lumberjack.setup_warnings_logger("DFW.Broker")
    except:
        pass

def main():
    """Run the router from the command line."""
    import argparse, six
    parser = argparse.ArgumentParser(description="A broker to connect ZMQ clients to services.")
    parser.add_argument("-c", "--config", type=six.text_type, help="set the Cauldron-zmq configuration filename", default=None)
    parser.add_argument("-v", "--verbose", action="count", help="use verbose messaging.")
    opt = parser.parse_args()
    if opt.verbose:
        _setup_logging(opt.verbose)
    print("^C to stop broker.")
    try:
        ZMQBroker.serve(read_configuration(opt.config))
    except KeyboardInterrupt:
        raise
    print("\nShutting down.")
    return 0