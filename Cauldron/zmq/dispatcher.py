# -*- coding: utf-8 -*-
"""
Dispatcher implementation for ZMQ

"""

from .common import zmq_dispatcher_address, zmq_broadcaster_address, check_zmq, teardown, ZMQCauldronMessage, ZMQCauldronParserError, ZMQCauldronErrorResponse, ZMQCauldronParserError
from .router import register, _shutdown_router
from ..base import DispatcherService, DispatcherKeyword
from .. import registry
from ..exc import DispatcherError

import threading
import logging
import weakref
import six
import time

__all__ = ["Service", "Keyword"]


registry.dispatcher.teardown_for('zmq')(teardown)

class _ZMQResponderThread(threading.Thread):
    """A python thread for ZMQ responses."""
    def __init__(self, service):
        self.service = weakref.proxy(service)
        self.log = logging.getLogger(self.service.log.name + ".Responder")
        self.running = threading.Event()
        super(_ZMQResponderThread, self).__init__(name="ZMQResponderThread-{0:s}".format(self.service.name))
        
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
        
        
    def handle_modify(self, message):
        """Handle a modify command."""
        return message.keyword.modify(message.payload)
    
    def handle_update(self, message):
        """Handle an update command."""
        return message.keyword.update()
        
    def handle_identify(self, message):
        """Handle an identify command."""
        return "yes" if message.payload in message.service else "no"
        
    def handle_enumerate(self, message):
        """Handle enumerate command."""
        return ":".join(message.service.keywords())
        
    def handle_broadcast(self, message):
        """Handle the broadcast command."""
        if not hasattr(self, '_broadcast_socket'):
            message.raise_error_response("Can't broadcast when responder thread hasn't started.")
        self._broadcast_socket.send("broadcast:{0}:{1}:{2}".format(self.service.name, message.keyword.name, message.payload))
        return "success"
    
    def run(self):
        """Run the thread."""
        zmq = check_zmq()
        try:
            ctx = self.service.ctx # Grab the context from the parent thread.
            socket = ctx.socket(zmq.REP)
            
            # Set up our switching poller to allow shutdown to come through.
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            
            try:
                address = zmq_dispatcher_address(self.service._config, bind=True)
                socket.bind(address)
            except zmq.ZMQError as e:
                self.log.error("Service can't bind to address '{0}' because {1}".format(address, e))
                raise
                
            self._broadcast_socket = ctx.socket(zmq.PUB)
            try:
                address = zmq_broadcaster_address(self.service._config, bind=True)
                self._broadcast_socket.bind(address)
            except zmq.ZMQError as e:
                self.log.error("Service can't bind to broadcaster address '{0}' because {1}".format(address, e))
                raise
                
            self.running.set()
            self.log.log(10, "Starting service loop.")
            while self.running:
                ready = dict(poller.poll(timeout=10.0))
                if ready.get(socket) == zmq.POLLIN:
                    self.respond(socket)
                
        except weakref.ReferenceError as e:
            self.log.info("Service reference error, shutting down, {0}".format(repr(e)))
        except zmq.ContextTerminated as e:
            self.log.info("Service shutdown and context terminated, closing command thread.")
            # We need to return here, because the socket was closed when the context terminated.
            return
        except zmq.ZMQError as e:
            self.log.info("ZMQ Error '{0}' terminated thread.".format(e))
            return
        finally:
            self.running.clear()
        
        socket.setsockopt(zmq.LINGER, 0)
        socket.close()
        
        try:
            self._broadcast_socket.setsockopt(zmq.LINGER, 0)
            self._broadcast_socket.close()
        except zmq.ZMQError as e:
            pass
        finally:
            del self._broadcast_socket
        
        return
        
    
    def respond(self, socket):
        """Respond to the command socket."""
        message = ZMQCauldronMessage.parse(socket.recv(), self.service)
        socket.send(six.binary_type(self.respond_message(message)))
            
    def respond_message(self, message):
        """Respond to a message."""
        try:
            self.log.debug("Handling '{0}'".format(str(message)))
            response = self.handle(message)
        except (ZMQCauldronErrorResponse, ZMQCauldronParserError) as e:
            return e.response
        else:
            return response
    
    def stop(self):
        """Stop the responder thread."""
        pass
    


@registry.dispatcher.service_for("zmq")
class Service(DispatcherService):
    """A ZMQ-based service."""
    def __init__(self, name, config, setup=None, dispatcher=None):
        zmq = check_zmq()
        self.ctx = zmq.Context()
        self._sockets = threading.local()
        super(Service, self).__init__(name, config, setup, dispatcher)
        
    @property
    def socket(self):
        """A thread-local ZMQ socket for sending commands to the responder thread."""
        # Short out if we already have a socket.
        if hasattr(self._sockets, 'socket'):
            return self._sockets.socket
        
        zmq = check_zmq()
        socket = self.ctx.socket(zmq.REQ)
        try:
            address = zmq_dispatcher_address(self._config)
            socket.connect(address)
        except zmq.ZMQError as e:
            self.log.error("Service can't connect to responder address '{0}' because {1}".format(address, e))
            raise
        else:
            self.log.debug("Connected to {0}".format(address))
            self._sockets.socket = socket
        return socket
        
    def _prepare(self):
        """Begin this service."""
        zmq = check_zmq()
        
        if self._config.getboolean("zmq-router", "enable"):
            register(self)
        
        self._thread = _ZMQResponderThread(self)
        self._message_queue = []
    
    def _begin(self):
        """Allow command responses to start."""
        
        if not self._thread.is_alive():
            self._thread.start()
            self.log.debug("Started ZMQ Responder Thread.")
            
        self._thread.running.wait(1.0)
        if not self._thread.running.is_set():
            raise DispatcherError("The dispatcher responder thread did not start.")
        
        while len(self._message_queue):
            self.socket.send(six.binary_type(self._message_queue.pop()))
            response = ZMQCauldronMessage.parse(self.socket.recv(), self)
        
    def shutdown(self):
        """Shutdown this object."""
        zmq = check_zmq()
        if hasattr(self, '_thread') and self._thread.is_alive():
            self._thread.stop()
        if hasattr(self, '_router'):
            _shutdown_router(self)
        self.ctx.destroy()
        
    def __missing__(self, key):
        """Allows the redis dispatcher to populate any keyword, whether it should exist or not."""
        return Keyword(key, self)
        
    def _synchronous_command(self, command, payload, keyword=None):
        """Execute a synchronous command."""
        message = ZMQCauldronMessage(command, self, keyword, payload, "REQ")
        if threading.current_thread() == self._thread:
            return self._thread.respond_message(message)
        elif not self._thread.running.is_set():
            return self._message_queue.append(message)
        elif not self._thread.is_alive():
            return self._thread.respond_message(message)
        else:
            self.socket.send(six.binary_type(message))
            return ZMQCauldronMessage.parse(self.socket.recv(), self)
        

@registry.dispatcher.keyword_for("zmq")
class Keyword(DispatcherKeyword):
    """A keyword object for ZMQ Cauldron backends."""
    
    def _broadcast(self, value):
        """Broadcast this keyword value."""
        self.service._synchronous_command("broadcast", value, self)
        