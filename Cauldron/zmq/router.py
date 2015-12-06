# -*- coding: utf-8 -*-
"""
A router to direct ZMQ services across different ports and addresses.
"""

from ..config import read_configuration
from ..exc import DispatcherError
from .common import check_zmq, zmq_router_address, zmq_dispatcher_host, ZMQCauldronMessage, ZMQCauldronErrorResponse, ZMQCauldronParserError

from six.moves import range
import logging
import time
import threading
import six

__all__ = ['ZMQRouter', 'register', 'lookup', 'main']

class ZMQRouterUnavailalbe(DispatcherError):
    """Error raised when a ZMQ router is unavailable."""
    pass

class ZMQRouter(object):
    """A router maintains a registry of services, and tells clients how to connect to a service."""
    def __init__(self, config=None, context=None):
        super(ZMQRouter, self).__init__()
        self.config = read_configuration(config)
        zmq = check_zmq()
        self.ctx = context or zmq.Context()
        self._listen = self.ctx.socket(zmq.REP)
        self._directory = {}
        self._port = iter(range(self.config.getint("zmq-router", "first-port"), self.config.getint("zmq-router", "last-port"), 2))
        self._shutdown = threading.Event()
        self.log = logging.getLogger("DFW.Router.zmq")
        self.log.debug("Router serving ports between {0} and {1}".format(self.config.getint("zmq-router", "first-port"), self.config.getint("zmq-router", "last-port")))
        
        if self.config.getint("zmq-router", "verbose"):
            _setup_logging(self.config.getint("zmq-router", "verbose"))
        
    def connect(self):
        """Connect to a listener."""
        address = zmq_router_address(self.config, bind=True)
        self._listen.bind(address)
        self.log.info("Started Router on {0}".format(address))
        
    def generate_new_address(self, service, host):
        """A function to generate a new address for a service."""
        # Brand-new service, give it some port numbers.
        port = next(self._port)
        bport = port + 1
        self._directory[service] = (host, port, bport)
        return (host, port, bport)
        
    def handle_register(self, message):
        """Handle a registration message."""
        service = message.service_name
        if service not in self._directory:
            host, port, bport = self.generate_new_address(service, message.payload)
            self.log.info("Registered service '{0}' at {1}:({2},{3})".format(service, host, port, bport))
        elif self._directory[service][0] != message.payload:
            # Updated host name, but retain port numbers.
            host, port, bport = self._directory[service]
            self._directory[service] = (message.payload, port, bport)
            self.log.info("Moved service '{0}' from {1} to {2}".format(service, host, message[2]))
        else:
            self.log.debug("Confirming re-registration of service '{0}'".format(service))
        # Respond with data.
        host, port, bport = self._directory[service]
        return ":".join(map(six.binary_type, [host, port, bport]))
        
    def handle_lookup(self, message):
        """Handle a message lookup."""
        try:
            host, port, bport = self._directory[message.service_name]
            self.log.debug("Looked up service '{0}' at {1}:({2},{3})".format(message.service_name, host, port, bport))
        except KeyError:
            host, port, bport = self.generate_new_address(service, message.payload)
            self.log.info("Created service '{0}' at {1}:({2},{3})".format(service, host, port, bport))
        return ":".join(map(six.binary_type, [host, port, bport]))
        
    def handle_shutdown(self, message):
        """Handle a shutdown message."""
        self.log.info("Router shutdown requested by service '{0}'".format(message.service))
        self._shutdown.set()
        return "acknowledged"
        
    def handle(self, message):
        """Handle a message."""
        method_name = "handle_{0:s}".format(message.command)
        if not hasattr(self, method_name):
            message.raise_error_response("Bad command '{0:s}'!".format(message['command']))
        try:
            response = getattr(self, method_name)(message)
        except ZMQCauldronErrorResponse as e:
            raise
        except Exception as e:
            self.log.error(repr(e))
            message.raise_error_response(repr(e))
        return message.response(response)
        
    def respond(self, socket):
        """Respond to the command socket."""
        message = ZMQCauldronMessage.parse(socket.recv_multipart())
        response = self.respond_message(message)
        self.log.log(5, "Responding |{0!s}|".format(response))
        socket.send_multipart(response.data)
            
    def respond_message(self, message):
        """Respond to a message."""
        try:
            self.log.log(5, "Handling |{0}|".format(str(message)))
            response = self.handle(message)
        except (ZMQCauldronErrorResponse, ZMQCauldronParserError) as e:
            return e.response
        else:
            return response
        
    def run(self):
        """Run the router."""
        self.connect()
        while not self._shutdown.is_set():
            if self._listen.poll(timeout=0.01):
                self.respond(self._listen)
        
        
    @classmethod
    def serve(cls, config=None):
        """Serve this router for as long as necessary."""
        obj = cls(config)
        obj.run()
        
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
        import threading
        thread = threading.Thread(target=cls.serve, args=(config,), name="ZMQRouter")
        thread.daemon = True
        thread.start()
        return thread
    

def _setup_logging(verbose):
    """Try to use lumberjack to enable logging when in a subprocess."""
    try:
        import lumberjack
        lumberjack.setup_logging("DFW.Router", mode='stream', level=30 - 10 * verbose)
        lumberjack.setup_warnings_logger("DFW.Router")
    except:
        pass

def main():
    """Run the router from the command line."""
    import argparse, six
    parser = argparse.ArgumentParser(description="A router to connect ZMQ clients to services.")
    parser.add_argument("-c", "--config", type=six.text_type, help="set the Cauldron-zmq configuration filename", default=None)
    parser.add_argument("-v", "--verbose", action="count", help="use verbose messaging.")
    opt = parser.parse_args()
    if opt.verbose:
        _setup_logging(opt.verbose)
    print("^C to stop router.")
    try:
        ZMQRouter.serve(opt.config)
    except KeyboardInterrupt:
        pass
    print("\nShutting down.")
    return 0

def register(service):
    """Register a service with the router."""
    zmq = check_zmq()
    socket = service.ctx.socket(zmq.REQ)
    
    try:
        # Connect to the router.
        address = zmq_router_address(service._config, bind=False)
        socket.connect(address)
        message = ZMQCauldronMessage("register", service, payload=zmq_dispatcher_host(service._config))
        
        socket.send_multipart(message.data)
    
        timeout = service._config.getint("zmq-router", "timeout")
    
        # We use a poller here so that we can bail if the router isn't online.
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
    
        socks = dict(poller.poll(timeout))
        if socks.get(socket) == zmq.POLLIN:
            # We are good to go!
            pass
        elif hasattr(service, '_router'):
            # Hmm, something is really broken here, as we have already made our very own
            # router, but we can't seem to connect to it.
            raise ZMQRouterUnavailalbe("Service has a built-in router at '{0}', but can't be reached.".format(address))
        else:
            if not service._config.getboolean("zmq-router", "allow-spawn"):
                raise ZMQRouterUnavailalbe("Can't locate router at '{0}', and allow-spawn=False, so not starting a new router.".format(address))
            
            # We probably need to start our own router.
            # Note that this router will only live as long as our primary service lives.
            if service._config.get("zmq-router", "process") == "thread":
                router = ZMQRouter.thread(service._configuration_location)
            else:
                router = ZMQRouter.daemon(service._configuration_location)
            service.log.info("Can't locate router at {0}, starting {1} router.".format(address,
                "thread" if service._config.get("zmq-router", "process") == "thread" else "subprocess"))
            
            # Disconnect the old socket.
            poller.unregister(socket)
            socket.setsockopt(zmq.LINGER, 0)
            socket.close()
            
            # Reconnect with a new socket.
            socket = service.ctx.socket(zmq.REQ)
            socket.connect(address)
            poller.register(socket, zmq.POLLIN)
            
            socket.send_multipart(message.data)
            
            socks = dict(poller.poll(timeout))
            if socks.get(socket) != zmq.POLLIN:
                raise ZMQRouterUnavailalbe("Couldn't manage to start router in subprocess at '{0}'. {1!r}".format(address, router))
            service._router = router
    
        message = ZMQCauldronMessage.parse(socket.recv_multipart())
    except Exception as e:
        service.log.error(e)
        raise
    else:
        return _handle_response(service, message)
    finally:
        socket.setsockopt(zmq.LINGER, 0)
        socket.close()
    

def lookup(service):
    """Lookup a service in the registry."""
    zmq = check_zmq()
    socket = service.ctx.socket(zmq.REQ)
    
    try:
        # Connect to the router.
        address = zmq_router_address(service._config, bind=False)
        socket.connect(address)
        
        
        socket.send_multipart(ZMQCauldronMessage("lookup", service, payload=zmq_dispatcher_host(service._config)).data)

        timeout = service._config.getint("zmq-router", "timeout")
        
        socket.poll(timeout)
        message = ZMQCauldronMessage.parse(socket.recv_multipart())
    except Exception as e:
        service.log.error(e)
        raise
    else:
        return _handle_response(service, message)
    finally:
        socket.setsockopt(zmq.LINGER, 0)
        socket.close()

def _handle_response(service, message):
    """Handle the message response, applying results to the configuration."""
    command = message.command
    service_name = message.service_name
    host, port, bport = message.payload.split(":",3)
    port = int(port)
    bport = int(bport)
    
    service._config.set("zmq", "host", str(host))
    service._config.set("zmq", "dispatch-port", str(port))
    service._config.set("zmq", "broadcast-port", str(bport))
    service.log.log(5, "{0} {1} response: {2}:({3},{4}).".format(service.name, command, host, port, bport))
    return host, port, bport
    
def shutdown_router(ctx = None, config = None, name = None):
    """Shutdown a router."""
    zmq = check_zmq()
    ctx = ctx or zmq.Context.instance()
    config = read_configuration(config)
    try:
        # Make a socket.
        socket = ctx.socket(zmq.REQ)
        timeout = config.getint("zmq-router", "timeout")
    except zmq.ZMQError as e:
        return False # If we can't get ZMQ to work, there is nothing to do here.
    try:
        # Connect to the router.
        socket.connect(zmq_router_address(config, bind=False))
        socket.send_multipart(ZMQCauldronMessage(command='shutdown', service=name).data)
        socket.poll(timeout)
        message = ZMQCauldronMessage.parse(socket.recv_multipart())
    except zmq.ZMQError as e:
        pass
    finally:
        socket.setsockopt(zmq.LINGER, 0)
        socket.close()
    return message.payload == 'acknowledged'

def _shutdown_router(service):
    """Shutdown a router attached to a service."""
    if not service._router.is_alive():
        return #nothing to do here!
    success = shutdown_router(service.ctx, service._config, service.name)
    if success:
        del service._router

    