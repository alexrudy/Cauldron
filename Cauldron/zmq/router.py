# -*- coding: utf-8 -*-
"""
A router to direct ZMQ services across different ports and addresses.
"""

from ..config import read_configuration
from .common import check_zmq, zmq_router_address, zmq_dispatcher_host

from six.moves import range
import logging

__all__ = ['ZMQRouter', 'register', 'lookup', 'main']

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
        self.log = logging.getLogger("DFW.Router.zmq")
        
    def connect(self):
        """Connect to a listener."""
        address = zmq_router_address(self.config, bind=True)
        self._listen.bind(address)
        self.log.info("Started Router on {0}".format(address))
        
    def run(self):
        """Run the router."""
        self.connect()
        while True:
            message = self._listen.recv_multipart()
            if not len(message) > 2:
                self._listen.send_multipart(["COMMAND ERROR: UNKNOWN MESSAGE"] + message)
                continue
            command = message[0]
            service = message[1]
            if command == "register":
                if service not in self._directory:
                    # Brand-new service, give it some port numbers.
                    port = next(self._port)
                    bport = port + 1
                    host = message[2]
                    self._directory[service] = (host, port, bport)
                    self.log.info("Registered service '{0}' at {1}:({2},{3})".format(service, host, port, bport))
                elif self._directory[service][0] != message[2]:
                    # Updated host name, but retain port numbers.
                    host, port, bport = self._directory[service]
                    self._directory[service] = (message[2], port, bport)
                    self.log.info("Moved service '{0}' from {1} to {2}".format(service, host, message[2]))
                else:
                    self.log.debug("Confirming re-registration of service '{0}'".format(service))
                # Respond with data.
                host, port, bport = self._directory[service]
                self._listen.send_multipart([command, service, host, str(port), str(bport)])
            elif command == "lookup":
                host, port, bport = self._directory.get(service, ("unknown", 0, 0))
                self.log.debug("Looked up service '{0}' at {1}:({2},{3})".format(service, host, port, bport))
                self._listen.send_multipart([command, service, host, str(port), str(bport)])
            elif command == "shutdown":
                self._listen.send_multipart([command, service, "acknowledged"])
                self.log.info("Router shutdown requested by service '{0}'".format(service))
                break
            else:
                self._listen.send_multipart([command, service, "error: command unknown"])
                
        
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
    
        socket.send_multipart(["register", service.name, zmq_dispatcher_host(service._config)])
    
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
            raise RuntimeError("This is really strange!")
        else:
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
            
            socket.send_multipart(["register", service.name, zmq_dispatcher_host(service._config)])
            
            socks = dict(poller.poll(timeout))
            if socks.get(socket) != zmq.POLLIN:
                raise RuntimeError("Couldn't manage to start router in subprocess. {0!r}".format(router))
            service._router = router
    
        message = socket.recv_multipart()
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

        socket.send_multipart(["lookup", service.name, zmq_dispatcher_host(service._config)])

        timeout = service._config.getint("zmq-router", "timeout")
        
        socket.poll(timeout)
        message = socket.recv_multipart()
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
    service_name = message[0]
    command = message[1]
    host = message[2]
    port = int(message[3])
    bport = int(message[4])
    
    service._config.set("zmq", "host", str(host))
    service._config.set("zmq", "dispatch-port", str(port))
    service._config.set("zmq", "broadcast-port", str(bport))
    return host, port, bport

def _shutdown_router(service):
    """Shutdown a router attached to a service."""
    zmq = check_zmq()
    socket = service.ctx.socket(zmq.REQ)
    timeout = service._config.getint("zmq-router", "timeout")
    try:
        # Connect to the router.
        socket.connect(zmq_router_address(service._config, bind=False))
        socket.send_multipart(["shutdown", service.name])
        socket.poll(timeout)
        message = socket.recv_multipart()
    except zmq.ZMQError as e:
        pass
    finally:
        socket.setsockopt(zmq.LINGER, 0)
        socket.close()
    if message[2] == 'acknowledged':
        del service._router
    return message[2] == 'acknowledged'
    