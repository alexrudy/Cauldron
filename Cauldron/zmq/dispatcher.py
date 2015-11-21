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

registry.dispatcher.teardown_for('zmq')(teardown)

class _ZMQResponderThread(threading.Thread):
    """A python thread for ZMQ responses."""
    def __init__(self, service):
        super(_ZMQResponderThread, self).__init__()
        self._shutdown = threading.Event()
        self.service = weakref.proxy(service)
        self.log = logging.getLogger("DFW.Service.Thread")
        self.daemon = True
        
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
        return  message.response(response)
        
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
        ctx = self.service.ctx
        socket = ctx.socket(zmq.REP)
        try:
            try:
                address = zmq_dispatcher_address(self.service._config, bind=True)
                socket.bind(address)
            except zmq.ZMQError as e:
                self.log.info("Service can't bind to address '{0}' because {1}".format(address, e))
                
            while not self._shutdown.isSet():
                try:
                    message = ZMQCauldronMessage.parse(socket.recv(), self.service)
                    response = self.handle(message)
                except (ZMQCauldronErrorResponse, ZMQCauldronParserError) as e:
                    socket.send(e.response)
                else:
                    socket.send(str(response))
        except weakref.ReferenceError as e:
            self.log.info("Service reference error, shutting down, {0}".format(repr(e)))
        except zmq.ContextTerminated as e:
            self.log.info("Service shutdown and context terminated, closing command thread.")
        socket.close()
        return
        
    
    def stop(self):
        """Stop the responder thread."""
        self._shutdown.set()
    


@registry.dispatcher.service_for("zmq")
class Service(DispatcherService):
    """A ZMQ-based service."""
    def __init__(self, name, config, setup=None, dispatcher=None):
        zmq = check_zmq()
        self.ctx = zmq.Context()
        self._broadcast_socket = self.ctx.socket(zmq.PUB)
        self._thread = _ZMQResponderThread(self)
        super(Service, self).__init__(name, config, setup, dispatcher)
        
    def _prepare(self):
        """Begin this service."""
        if self._config.getboolean("zmq-router", "enable"):
            register(self)
        
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
            self._broadcast_socket.setsockopt(zmq.LINGER, 0)
            self._broadcast_socket.close()
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
        
        