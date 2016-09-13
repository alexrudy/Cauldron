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
from .protocol import ZMQCauldronMessage, ZMQCauldronErrorResponse, FRAMEBLANK, FRAMEFAIL, DIRECTIONS
from .common import zmq_get_address, check_zmq, teardown, zmq_connect_socket
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
            binascii.hexlify(self.id).decode('utf-8')[:6], len(self.pending), self.timeout - time.time(), len(self.responses)
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
        self.pending.remove(dispatcher.id)
        if message.payload not in (FRAMEBLANK.decode('utf-8'), FRAMEFAIL.decode('utf-8')) and not DIRECTIONS.iserror(message.direction):
            self.responses[dispatcher.name] = message.payload
            self.client.log.log(5, "{0!r}.add({1!r}) success".format(self, message))
        else:
            self.client.log.log(5, "{0!r}.add({1!r}) ignore".format(self, message))
        
    def resolve(self):
        """Fan message responses."""
        if not self.valid:
            response = self.message.error_response("No dispatchers for '{0}'".format(self.message.service))
            self.client.log.log(5, "{0!r}.resolve() no dispatcher".format(self))
            return response
        elif len(self.responses) == 1:
            dispatcher, payload = next(iter(self.responses.items()))
            response = self.message.response(payload)
            response.dispatcher = dispatcher
            self.client.log.log(5, "{0!r}.resolve() single response {1}".format(self, payload))
            return response
        elif len(self.responses):
            self.client.log.log(5, "{0!r}.resolve() multiple response {1!r}".format(self, self.responses))
            return self.message.response(":".join(self.responses.values()))
        else:
            self.client.log.log(5, "{0!r}.resolve() failure".format(self))
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
        self._next_beat = time.time() + self.service.broker.timeout
        
    @property
    def alive(self):
        """Is this object alive?"""
        return time.time() < (self._expiration + 4 * self.service.broker.timeout)
        
    @property
    def shouldbeat(self):
        """Should this thing ask for a heartbeat."""
        return time.time() > self._next_beat
        
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
            key, value = self._message_pool.popitem()
            yield value
            
    def clear(self):
        """Clear the message pool"""
        self._message_pool.clear()
    
    def __repr__(self):
        return "<{0} name='{1}' lifetime={2:.2f} open={3:d}>".format(self.__class__.__name__, self.name, self.lifetime, self.active)

class Client(Lifetime):
    """A simple representation of a client connection."""
    def __init__(self, client_id, service):
        super(Client, self).__init__(service)
        self.id = client_id
        self.name = binascii.hexlify(self.id).decode('utf-8')
        self.log = logger_getChild(service.log, "Client.{0}".format(binascii.hexlify(self.id)))
    
    def send(self, message, socket):
        """Send a message to this client."""
        message.prefix = [self.id, b""]
        self.log.log(5, "{0!r}.send({1!r})".format(self, message))
        socket.send_multipart(message.data)
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
        self.log.log(5, "{0!r}.send({1!r})".format(self, message))
        socket.send_multipart(message.data)
        self.activate(message)
        
    def send_beat(self, socket):
        """Send a beat."""
        if self.message is not None:
            msg = ZMQCauldronMessage(command='heartbeat', direction="DBP",
                service=self.service.name, dispatcher=self.name, payload="beat")
            msg.prefix = [self.id, b""]
            self._next_beat = time.time() + self.service.broker.timeout
            self.log.log(5, "{0!r}.beat({1!r})".format(self, msg))
            socket.send_multipart(msg.data)
            self.activate(msg)
        
        


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
            self.log.log(5, "{0!r}.recv({1})".format(dispatcher_object, message))
            dispatcher_object.deactivate(message)
        return dispatcher_object
        
    def get_client(self, message, recv=True):
        """Retrieve a client object by client ID."""
        try:
            client_object = self.clients[message.client_id]
        except KeyError:
            client_object = self.clients[message.client_id] = Client(message.client_id, self)
        if recv:
            self.log.log(5, "{0!r}.recv({1})".format(client_object, message))
        return client_object
        
    def scrape(self, message):
        """Scrape a message for dispatcher information."""
        # Cache dispatcher identities for easy lookup later.
        if message.dispatcher != FRAMEBLANK.decode('utf-8'):
            if message.isvalid:
                # If this message can identify the disptacher, save it for later.
                self.keywords[message.keyword.upper()] = message.dispatcher
            if message.command == "identify" and message.isvalid:
                self.dispatchers[message.dispatcher].keywords[message.keyword.upper()] = message.payload
            
    
    def paste(self, message):
        """Opposite of scrape, paste the dispatcher back into the message."""
        if message.dispatcher == FRAMEBLANK.decode('utf-8'):
            # Locate the correct dispatcher.
            if message.keyword != FRAMEBLANK.decode('utf-8'):
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
        for name in list(self.dispatchers.keys()):
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
            if dispatcher.shouldbeat:
                dispatcher.send_beat(socket)
        
    def handle(self, message, socket):
        """Handle"""
        try:
            method = getattr(self, handlers[message.direction])
            method(message, socket)
        except KeyError as e:
            raise
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
            pass
            
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
        try:
            self._fans[message.identifier].add(dispatcher, message)
        except KeyError:
            # Nothing to do, the message was probably disposed much earlier.
            pass
    
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
            self._fans[fmessage.id] = fmessage
        
            for dispatcher in self.dispatchers.values():
                dispatcher.send(fmessage.generate_message(dispatcher), socket)
            self.log.log(5, "{0!r}.fan()".format(fmessage))
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
            response = message.response(self.broker._mon_address)
        elif message.command == "locate":
            # The client has asked us if a service is locatable.
            response = message.response("yes" if len(self.dispatchers) else "no")
        else:
            response = message.error_response("unknown command")
        
        client.send(response, socket)



class ZMQBroker(threading.Thread):
    """A broker object for handling ZMQ Messaging patterns"""
    def __init__(self, name, address, pub_address, sub_address, mon_address, context=None, timeout=1.0):
        super(ZMQBroker, self).__init__(name=name)
        import zmq
        self.context = context or zmq.Context.instance()
        self.running = threading.Event()
        self.log = logging.getLogger("DFW.Broker." + name )
        self._address = address
        self._pub_address = pub_address
        self._sub_address = sub_address
        self._mon_address = mon_address
        self.timeout = float(timeout)
        self._local = threading.local()
        self._error = None
        self.services = dict()
        
    @classmethod
    def from_config(cls, config, name="ConfiguredBroker"):
        """Make a new item from a configuration."""
        config = read_configuration(config)
        address = zmq_get_address(config, "broker", bind=True)
        sub_address = zmq_get_address(config, "publish", bind=True)
        pub_address = zmq_get_address(config, "subscribe", bind=True)
        mon_address = zmq_get_address(config, "subscribe", bind=False)
        timeout = config.getfloat("zmq", "timeout")
        return cls(name, address, pub_address, sub_address, mon_address, timeout=timeout)
        
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
        proc = mp.Process(target=cls.serve, args=(config,), name="ProcessBroker")
        proc.daemon = daemon
        proc.start()
        return proc
    
    @classmethod
    def thread(cls, config=None, daemon=True):
        """Serve in a thread."""
        obj = cls.from_config(config, name="ThreadBroker")
        obj.daemon = daemon
        obj.start()
        return obj
        
    @classmethod
    def setup(cls, config=None, timeout=2.0, daemon=True):
        """Ensure a broker is set up to start."""
        if not cls.check(timeout=timeout):
            b = cls.thread(config=config, daemon=daemon)
            b.running.wait(timeout=min([timeout, 2.0]))
            if not b.running.is_set():
                msg = "Couldn't start ZMQ broker."
                if b._error is not None:
                    msg += " Error: " + repr(b._error)
                raise RuntimeError(msg)
            return b
        else:
            return None
    
    @classmethod
    def check(cls, config=None, timeout=2.0, ctx=None, address=None):
        """Check for the existence of a router at the configured address."""
        import zmq
        ctx = ctx or zmq.Context.instance()
        log = logging.getLogger(__name__ + "Broker.check")
        
        socket = ctx.socket(zmq.REQ)
        zmq_connect_socket(socket, read_configuration(config), "broker", log=log, label="broker-check", address=address)
        
        message = ZMQCauldronMessage(command="check", direction="UBQ")
        socket.send_multipart(message.data)
        if socket.poll(timeout * 1e3):
            response = ZMQCauldronMessage.parse(socket.recv_multipart())
            print(response)
            if response.payload == "Broker Alive":
                return True
        return False
    
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
        
    
    def respond_inquiry(self, message, socket):
        """Respond to an inquiry."""
        try:
            socket.send_multipart(message.response("Broker Alive").data)
        except Exception as e:
            socket.send_multipart(message.error_response(repr(e)).data)
    
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
        signal = self._local.signal = self.connect("inproc://{0}".format(hex(id(self))), "PULL")
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
            signal.recv(flags=zmq.DONTWAIT)
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
            sockets = dict(poller.poll(timeout=self.timeout))
            
            if sockets.get(signal) == zmq.POLLIN:
                self.running.clear()
                return
            
            if sockets.get(socket) == zmq.POLLIN:
                request = socket.recv_multipart()
                if len(request) > 3:
                    message = ZMQCauldronMessage.parse(request)
                    if message.direction[0:2] == "UB":
                        self.respond_inquiry(message, socket)
                    else:
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
            self.log.log(6, "Ending .respond(). {0!r}".format(e))
            self.running.clear()
            
        
    
    def stop(self, timeout=None):
        """Stop the responder."""
        import zmq
        
        if not self.isAlive():
            return
        
        if self.running.is_set() and not self.context.closed:
            signal = self.context.socket(zmq.PUSH)
            signal.connect("inproc://{0:s}".format(hex(id(self))))
            self.running.clear()
            signal.send(b"", flags=zmq.NOBLOCK)
            signal.close()
        else:
            self.running.clear()
        
        self.log.debug("Signaled to stop broker.")
        self.join(timeout=timeout)
        self.log.debug("Joined Broker")
        
        if self._error is not None:
            raise RuntimeError(self._error)

    def run(self):
        """Run method for threads."""
        try:
            self.prepare()
        
            self.running.set()
            self.log.debug("Broker running. Timeout={0}".format(self.timeout))
            while self.running.is_set():
                self.respond()
            
            self.close()
        except Exception as e:
            self._error = e
            raise
        else:
            self.log.debug("Broker done. running={0}".format(self.running.is_set()))
        
    

def _setup_logging(verbose):
    """Try to use lumberjack to enable logging when in a subprocess."""
    try:
        import lumberjack
        lumberjack.setup_logging(mode='stream', level=30 - 10 * verbose)
        lumberjack.setup_warnings_logger("DFW.Broker")
    except Exception as e:
        print(e)
        pass

def main():
    """Run the router from the command line."""
    import argparse, six
    parser = argparse.ArgumentParser(description="A broker to connect ZMQ clients to services.")
    parser.add_argument("-c", "--config", type=six.text_type, help="set the Cauldron-zmq configuration filename", default=None)
    parser.add_argument("-v", "--verbose", action="count", help="use verbose messaging.")
    parser.add_argument("-D", dest='debug', action='store_true', help="Debug - print keyboard interrupts.")
    opt = parser.parse_args()
    if opt.verbose:
        _setup_logging(opt.verbose)
    print("^C to stop broker.")
    try:
        ZMQBroker.serve(read_configuration(opt.config))
    except KeyboardInterrupt:
        if opt.debug:
            raise
    print("\nShutting down.")
    return 0