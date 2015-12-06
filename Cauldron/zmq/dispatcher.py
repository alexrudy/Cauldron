# -*- coding: utf-8 -*-
"""
Dispatcher implementation for ZMQ

"""

from .common import zmq_dispatcher_address, zmq_broadcaster_address, check_zmq, teardown
from .microservice import ZMQMicroservice, ZMQCauldronMessage, FRAMEFAIL
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

class _ZMQResponder(ZMQMicroservice):
    """A python thread for ZMQ responses."""
    
    _socket = None
    
    def __init__(self, service):
        self.service = weakref.proxy(service)
        super(_ZMQResponder, self).__init__(address=zmq_dispatcher_address(self.service._config, bind=True), context=self.service.ctx, name="ZMQResponder-{0:s}".format(self.service.name))
        self.log = logging.getLogger(self.service.log.name + ".Responder")
        
    def handle_modify(self, message):
        """Handle a modify command."""
        keyword = message.verify(self.service)
        keyword.modify(message.payload)
        return keyword.value
    
    def handle_update(self, message):
        """Handle an update command."""
        keyword = message.verify(self.service)
        return keyword.update()
        
    def handle_identify(self, message):
        """Handle an identify command."""
        if message.payload in message.service:
            return message.service[message.payload].KTL_TYPE
        else:
            return "no"
        
    def handle_enumerate(self, message):
        """Handle enumerate command."""
        message.verify(self.service)
        return ":".join(self.service.keywords())
        
    def handle_broadcast(self, message):
        """Handle the broadcast command."""
        message.verify(self.service)
        message = ZMQCauldronMessage(command="broadcast", service=self.service.name, dispatcher=self.service.dispatcher, keyword=message.keyword, payload=message.payload, direction="PUB")
        socket = self._get_broadcaster()
        self.log.log(5, "Broadcast |{0!s}|".format(message))
        socket.send_multipart(message.data)
        return "success"
    
    def _get_broadcaster(self):
        """Connect the broadcast socket."""
        zmq = check_zmq()
        if self._socket is not None:
            return self._socket
        self._socket = self.ctx.socket(zmq.PUB)
        try:
            address = zmq_broadcaster_address(self.service._config, bind=True)
            self._socket.bind(address)
        except zmq.ZMQError as e:
            self.log.error("Service can't bind to broadcaster address '{0}' because {1}".format(address, e))
            self._error = e
            raise
        else:
            self.log.log(5, "Broadcaster bound to {0}".format(address))
            time.sleep(0.2)
            return self._socket
    


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
            self.log.debug("Connected dispatcher to {0}".format(address))
            self._sockets.socket = socket
        return socket
        
    def _prepare(self):
        """Begin this service."""
        zmq = check_zmq()
        
        if self._config.getboolean("zmq-router", "enable"):
            register(self)
        
        self._thread = _ZMQResponder(self)
        self._message_queue = []
    
    def _begin(self):
        """Allow command responses to start."""
        
        if not self._thread.is_alive():
            self._thread.start()
            self.log.debug("Started ZMQ Responder Thread.")
            
        self._thread.check_alive()
        
        while len(self._message_queue):
            self.socket.send_multipart(self._message_queue.pop().data)
            response = ZMQCauldronMessage.parse(self.socket.recv_multipart())
            response.verify(self)
        
    def shutdown(self):
        """Shutdown this object."""
        zmq = check_zmq()
        if hasattr(self, '_thread') and self._thread.is_alive():
            self._thread.stop()
        if hasattr(self, '_router'):
            _shutdown_router(self)
        self.ctx.destroy()
        
    def _synchronous_command(self, command, payload, keyword=None):
        """Execute a synchronous command."""
        message = ZMQCauldronMessage(command, service=self.name, dispatcher=self.dispatcher,
            keyword=keyword.name if keyword else "\x01", payload=payload, direction="REQ")
        self.log.log(5, "Request |{0!s}|".format(message))
        if threading.current_thread() == self._thread or not self._thread.is_alive():
            response = self._thread.handle(message)
        elif not self._thread.running.is_set():
            return self._message_queue.append(message)
        else:
            self.socket.send_multipart(message.data)
            response = ZMQCauldronMessage.parse(self.socket.recv_multipart())
        response.verify(self)
        return response
        

@registry.dispatcher.keyword_for("zmq")
class Keyword(DispatcherKeyword):
    """A keyword object for ZMQ Cauldron backends."""
    
    def _broadcast(self, value):
        """Broadcast this keyword value."""
        self.service._synchronous_command("broadcast", value, self)
        