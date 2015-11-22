# -*- coding: utf-8 -*-
"""
Dispatcher implementation for ZMQ

"""

from .common import zmq_dispatcher_address, zmq_broadcaster_address, check_zmq, teardown, ZMQCauldronMessage, ZMQCauldronParserError, ZMQCauldronErrorResponse, ZMQCauldronParserError
from .router import register, _shutdown_router
from ..base import DispatcherService, DispatcherKeyword
from .. import registry

import threading
import logging
import weakref
import zmq
import six

__all__ = ["Service", "Keyword"]


registry.dispatcher.teardown_for('zmq')(teardown)

class _ZMQResponderThread(threading.Thread):
    """A python thread for ZMQ responses."""
    def __init__(self, service):
        self.service = weakref.proxy(service)
        self.log = self.service.log.getChild("Responder")
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
        
    
    def run(self):
        """Run the thread."""
        zmq = check_zmq()
        run = True
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
                
            self.log.log(5, "Starting service loop.")
            while run:
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
            
        signal.setsockopt(zmq.LINGER, 0)
        signal.close()
        socket.setsockopt(zmq.LINGER, 0)
        socket.close()
        return
        
    
    def respond(self, socket):
        """Respond to the command socket."""
        try:
            message = ZMQCauldronMessage.parse(socket.recv(), self.service)
            response = self.handle(message)
        except (ZMQCauldronErrorResponse, ZMQCauldronParserError) as e:
            socket.send(six.binary_type(e.response))
        else:
            socket.send(six.binary_type(response))
    
    def stop(self):
        """Stop the responder thread."""
        pass
    


@registry.dispatcher.service_for("zmq")
class Service(DispatcherService):
    """A ZMQ-based service."""
    def __init__(self, name, config, setup=None, dispatcher=None):
        zmq = check_zmq()
        self.ctx = zmq.Context()
        super(Service, self).__init__(name, config, setup, dispatcher)
        
    def _prepare(self):
        """Begin this service."""
        zmq = check_zmq()
        
        if self._config.getboolean("zmq-router", "enable"):
            register(self)
        
        self._thread = _ZMQResponderThread(self)
        self._broadcast_socket = self.ctx.socket(zmq.PUB)
        
        try:
            address = zmq_broadcaster_address(self._config, bind=True)
            self._broadcast_socket.bind(address)
        except zmq.ZMQError as e:
            self.log.error("Service can't bind to address '{0}' because {1}".format(address, e))
            raise
        
    
    def _begin(self):
        """Allow command responses to start."""
        if not self._thread.is_alive():
            self._thread.start()
        
    def shutdown(self):
        """Shutdown this object."""
        if hasattr(self, '_thread') and self._thread.is_alive():
            self._thread.stop()
        if hasattr(self, '_broadcast_socket'):
            try:
                self._broadcast_socket.setsockopt(zmq.LINGER, 0)
                self._broadcast_socket.close()
            except zmq.ZMQError as e:
                pass
            finally:
                del self._broadcast_socket
        if hasattr(self, '_router'):
            _shutdown_router(self)
        
        self.ctx.destroy()
        
    def __missing__(self, key):
        """Allows the redis dispatcher to populate any keyword, whether it should exist or not."""
        return Keyword(key, self)
        

@registry.dispatcher.keyword_for("zmq")
class Keyword(DispatcherKeyword):
    """A keyword object for ZMQ Cauldron backends."""
    
    def _broadcast(self, value):
        """Broadcast this keyword value."""
        self.service._broadcast_socket.send("broadcast:{0}:{1}:{2}".format(self.service.name, self.name, value))
        
        