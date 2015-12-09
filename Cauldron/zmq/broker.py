# -*- coding: utf-8 -*-
"""
A single message broker service to distribute messages between clients and dispatchers.
"""
from __future__ import absolute_import

import threading
import logging
import collections
import binascii

from ..config import read_configuration
from .microservice import ZMQCauldronMessage, ZMQCauldronErrorResponse, FRAMEBLANK, FRAMEFAIL
from .common import zmq_address
from ..exc import DispatcherError

CLIENT_DIRECTIONS = set(["REQ"])

class NoDispatcherAvailable(DispatcherError):
    """Raised when no dispatcher is available."""
    pass
    
class MultipleDispatchersFound(DispatcherError):
    """Raised when too many dispatchers are identified for a keyword."""
    pass
    
class Identification(object):
    """An identification message request"""
    def __init__(self, client_id, message, log):
        super(Identification, self).__init__()
        self.message = message # The original message.
        self.pending = set()
        self.identities = set()
        self.client_id = client_id
        self.log = log
        
    def resolve(self):
        """docstring for start"""
        if len(self.identities) == 1:
            dispatcher = self.identities.pop()
            self.log.log(5, "Identify success, dispatcher {0}".format(dispatcher))
            return dispatcher
        elif len(self.identities) == 0:
            self.log.log(5, "Identify failure for keyword {0}, no identities found.".format())
            raise NoDispatcherAvailable("No dispatcher found for service '{0}'".format(message.service))
        else:
            raise MultipleDispatchersFound("Found multiple dispatchers for {0}:{1}".format(message.service, message.keyword))
        

class Client(object):
    """A simple representation of a client connection."""
    def __init__(self, client_id):
        super(Client, self).__init__()
        self.id = client_id

class Dispatcher(object):
    """A simple representation of a dispatcher."""
    def __init__(self, name, dispatcher_id):
        super(Dispatcher, self).__init__()
        self.id = dispatcher_id
        self.name = name

class Service(object):
    """A simple representation of a service"""
    def __init__(self, name, log):
        super(Service, self).__init__()
        self.name = name.upper()
        self.keywords = {}
        self.dispatchers = {}
        self.log = log
        
        self._identifies = {}
        
    def get_dispatcher(self, dispatcher, dispatcher_id):
        """Try to get a service."""
        try:
            dispatcher_object = self.dispatchers[dispatcher]
        except KeyError:
            dispatcher_object = self.dispatchers[dispatcher] = Dispatcher(dispatcher, dispatcher_id)
        
        #TODO: I'm not sure that this is correct.
        # Always reset the identity. It might have changed, in which case we want to use the
        # version of this dispatcher which responded most recently.
        dispatcher_object.id = dispatcher_id
        return dispatcher_object
        
    def scrape(self, message):
        """Scrape a message for dispatcher information."""
        # Cache dispatcher identities for easy lookup later.
        if message.dispatcher != FRAMEBLANK:
            if message.payload != FRAMEFAIL and message.direction != "ERR" and message.keyword != FRAMEBLANK:
                # If this message can identify the disptacher, save it for later.
                self.keywords[message.keyword.upper()] = message.dispatcher
                
    def paste(self, message):
        """Opposite of scrape, paste the dispatcher back into the message."""
        if message.dispatcher == FRAMEBLANK:
            # Locate the correct dispatcher.
            if message.keyword != FRAMEBLANK:
                dispatcher = self.keywords.get(message.keyword.upper(), FRAMEFAIL)
                if dispatcher == FRAMEFAIL:
                    raise NoDispatcherAvailable("No dispatcher is available for '{0}'".format(message.service))
                dispatcher = self.dispatchers.get(dispatcher, FRAMEFAIL)
                message.dispatcher = dispatcher.name
            else:
                raise DispatcherError("Ambiguous dispatcher specification in message {0!s}".format(message))
        else:
            # Explicitly specified dispatcher.
            dispatcher = message.dispatcher
            dispatcher = self.dispatchers.get(dispatcher, FRAMEFAIL)
        return FRAMEFAIL if dispatcher == FRAMEFAIL else dispatcher.id
    
    def start_identify_messages(self, client_id, message):
        """Start an identify process, with a generator over identify messages."""
        identify_id = binascii.hexlify(client_id)
        self._identifies[identify_id] = identify = Identification(client_id, message, self.log)
        for dispatcher in self.dispatchers.values():
            identify.pending.add(dispatcher.id)
            self.log.log(5, "Requesting identify from {0}: {1!s}".format(binascii.hexlify(client_id), message))
            yield [dispatcher.id, b"", client_id, b""] + message.data
        if not len(self.dispatchers):
            self.log.log(5, "Identify failed because there are no registered dispatchers.")
            raise NoDispatcherAvailable("No dispatcher found for service '{0}'".format(message.service))
            
        
    def collect_identify_message(self, dispatcher_id, client_id, message):
        """Collect a single identify message."""
        identify_id = binascii.hexlify(client_id)
        identify = self._identifies[identify_id]
        identify.pending.remove(dispatcher_id)
        if message.payload != FRAMEFAIL and message.dispatcher not in [FRAMEFAIL,FRAMEBLANK]:
            identify.identities.add(message.dispatcher)
            
        if len(identify.pending):
            return FRAMEBLANK
        else:
            del self._identifies[identify_id]
            dispatcher = identify.resolve()
            self.keywords[identify.message.payload.upper()] = dispatcher
            return dispatcher
        
    def response(self, dispatcher_id, client_id, message):
        """Figure out the appropriate backend response."""
        if message.command == "identify":
            # Handle the special case, the explicity identify command.
            dispatcher = self.collect_identify_message(dispatcher_id, client_id, message)
            if dispatcher == FRAMEBLANK:
                message.service = FRAMEBLANK
            else:
                message.dispatcher = dispatcher
        elif message.command == "enumerate":
            
        return message

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
        
        self._active = list()
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
        obj.respond()
        
    @classmethod
    def daemon(cls, config=None):
        """Serve in a process."""
        import multiprocessing as mp
        proc = mp.Process(target=cls.serve, args=(config,), name="ZMQRouter")
        proc.daemon = True
        proc.start()
        return proc
    
    @classmethod
    def thread(cls, config=None):
        """Serve in a thread."""
        obj = cls.serve(config)
        obj.daemon = True
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
            service_object = self.services[service.upper()] = Service(service, self.log)
            self.log.log(5, "Registered new service '{0}'".format(service))
        return service_object
    
    def handle_dispatcher(self, request, socket):
        """Handle a dispatcher request."""
        message = ZMQCauldronMessage.parse(request)
        self.log.log(5, "Dispatcher Message: ({0}){1!s}".format(len(message.prefix), message))
        dispatcher_id, _, client_id = message.prefix[:3]
        if dispatcher_id in self._active:
            self._active.remove(dispatcher_id)
        message.prefix = []
        service_known = message.service in self.services
        
        service = self.get_service(message.service)
        dispatcher_known = message.dispatcher in service.dispatchers
        
        dispatcher = service.get_dispatcher(message.dispatcher, dispatcher_id)
        
        if client_id != FRAMEBLANK:
            # This is a reply to a specific client.
            try:
                message = service.response(dispatcher_id, client_id, message)
            except DispatcherError as e:
                message = message.error_response(repr(e))
            else:
                service.scrape(message)
        
            if message.service != FRAMEBLANK:
                # Pass the original reply on to the original requester.
                self.log.log(5, "Client reply: {0!s}".format(message))
                socket.send_multipart([client_id, b""] + message.data)
                if client_id in self._active:
                    self._active.remove(client_id)
            else:
                # If the service was blank, we discard the message.
                self.log.log(5, "Discarding dispatcher message {0!s}".format(message))
        else:
            # We have a new service.
            if dispatcher_known:
                self.log.log(5, "Re-identified dispatcher {0}".format(dispatcher.name))
            else:
                self.log.log(5, "Identified new dispatcher {0}".format(dispatcher.name))
            service.scrape(message)
            if message.command == "welcome":
                response = message.response("confirmed")
                socket.send_multipart([dispatcher_id, b""] + response.data)
            elif message.command == "ready":
                pass # Do nothing, the dispatcher is ready.
            else:
                self.log.log(5, "Malformed dispatcher command: {0!s}".format(message))
            
    def handle_client(self, request, socket):
        """Handle a client message."""
        client_id, _ = request[:2]
        message = ZMQCauldronMessage.parse(request[2:])
        
        if message.direction not in CLIENT_DIRECTIONS:
            self.log.log(5, "Mishandled client message: {0!s}".format(message))
            # socket.send_multipart()
            return
        
        self.log.log(5, "Client message {0!s}".format(message))
        service = self.get_service(message.service)
        
        try:
            if message.command == "identify":
                # Handle the identify command by asking all dispatchers.
                for identify_message in service.start_identify_messages(client_id, message):
                    socket.send_multipart(identify_message)
                    self._active.append(identify_message[0])
                # End early here, we've already sent what we needed.
                return
            elif message.command == "lookup":
                if message.payload == "subscribe":
                    # The client has asked for the subscription address, we should send that to them.
                    response = message.response(self._pub_address)
                else:
                    response = message.error_response("Unknown lookup value.")
                self.log.log(5, "Client lookup reply {0!s}".format(response))
                socket.send_multipart([client_id, b""] + response.data)
                if client_id in self._active:
                    self._active.remove(client_id)
                return
            elif message.command == "locate":
                # The client has asked us if a service is locatable.
                response = message.response("yes" if len(service.dispatchers) else "no")
                self.log.log(5, "Client locate reply {0!s}".format(response))
                socket.send_multipart([client_id, b""] + response.data)
                return
            else:
                dispatcher_id = service.paste(message)
            
            if dispatcher_id == FRAMEFAIL:
                raise NoDispatcherAvailable("No dispatcher is available for '{0}'".format(message.service))
        except DispatcherError as e:
            response =  message.error_response(repr(e))
            self.log.log(5, "Client error reply: {0!s}".format(response))
            socket.send_multipart([client_id, b""] +response.data)
            if client_id in self._active:
                self._active.remove(client_id)
        else:
            socket.send_multipart([dispatcher_id, b"", client_id, b""] + message.data)
            self._active.append(dispatcher_id)
    
    def respond(self):
        """Respond"""
        import zmq
        socket = self.connect(self._address)
        xpub = self.connect(self._pub_address, 'XPUB')
        xsub = self.connect(self._sub_address, 'XSUB')
        # xsub.subscribe = six.binary_type("")
        
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        poller.register(xsub, zmq.POLLIN)
        poller.register(xpub, zmq.POLLIN)
        
        self.running.set()
        self.log.debug("Broker running. Timeout={0}".format(self.timeout))
        while self.running.is_set() or len(self._active):
            sockets = dict(poller.poll(timeout=self.timeout * 1e3))
            if sockets.get(socket) == zmq.POLLIN:
                request = socket.recv_multipart()
                
                if len(request) > 3:
                    if request[-3] in CLIENT_DIRECTIONS:
                        self.handle_client(request, socket)
                    else:
                        self.handle_dispatcher(request, socket)
                else:
                    self.log.log(5, "Malofrmed request: |{0}|".format("|".join(request)))
            if sockets.get(xsub) == zmq.POLLIN:
                request = xsub.recv_multipart()
                xpub.send_multipart(request)
            if sockets.get(xpub) == zmq.POLLIN:
                request = xpub.recv_multipart()
                xsub.send_multipart(request)
            
            if not len(sockets):
                self.log.debug("Broker got nothing...")
            #TODO: Add heartbeats here.
        self.log.debug("Broker done.")
        
    
    def stop(self):
        """Stop the responder."""
        self.running.clear()
        
    def run(self):
        """Run method for threads."""
        self.respond()
        
    

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
        pass
    print("\nShutting down.")
    return 0