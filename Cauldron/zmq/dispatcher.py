# -*- coding: utf-8 -*-
"""
Dispatcher implementation for ZMQ

"""

from .common import zmq_get_address, check_zmq, teardown, zmq_connect_socket
from .microservice import ZMQMicroservice, ZMQCauldronMessage, FRAMEFAIL, FRAMEBLANK
from .broker import ZMQBroker
from ..base import DispatcherService, DispatcherKeyword
from .. import registry
from ..exc import DispatcherError, WrongDispatcher, TimeoutError

import threading
import logging
import weakref
import six
import time
import sys, traceback

__all__ = ["Service", "Keyword"]


registry.dispatcher.teardown_for('zmq')(teardown)

class _ZMQResponder(ZMQMicroservice):
    """A python thread for ZMQ responses."""
    
    _socket = None
    
    def __init__(self, service):
        self.service = weakref.proxy(service)
        address = zmq_get_address(self.service._config, "broker", bind=False)
        super(_ZMQResponder, self).__init__(address=address, use_broker=True,
            context=self.service.ctx, name="DFW.Service.{0:s}.Responder".format(self.service.name))
        
    def check_broker(self, socket, signal):
        """Check for broker liveliness."""
        zmq = check_zmq()
        
        welcome = ZMQCauldronMessage(command="welcome", service=self.service.name, dispatcher=self.service.dispatcher, direction="DBQ")
        socket.send_multipart(welcome.data)
        self.log.log(5, "Sent broker a welcome message: {0!s}.".format(welcome))
        
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        poller.register(signal, zmq.POLLIN)
        
        ready = dict(poller.poll(timeout=self.timeout * 1e3))
        if ready.get(socket) == zmq.POLLIN:
            message = ZMQCauldronMessage.parse(socket.recv_multipart())
            if message.payload != "confirmed":
                raise DispatcherError("Message confirming welcome was malformed! {0!s}".format(message))
            return True
        else:
            self.log.log(5, "No broker response was available.  ")
            return False
        
        
    def greet_broker(self, socket, signal):
        """Send the appropriate greeting to the broker."""
        checks = 1
        attempts = 0
        while checks:
            attempts += 1
            checks -= 1
            if self.check_broker(socket, signal):
                break
            self._b = ZMQBroker.daemon(config = self.service._config)
        else:
            raise TimeoutError("Can't connect to broker after {0:d} attempts.".format(attempts))
        
        ready = ZMQCauldronMessage(command="ready", service=self.service.name, dispatcher=self.service.dispatcher, direction="DBQ")
        socket.send_multipart(ready.data)
        self.log.log(5, "Sent broker a ready message: {0!s}.".format(ready))
        
    
    def handle_modify(self, message):
        """Handle a modify command."""
        message.verify(self.service)
        keyword = self.service[message.keyword]
        keyword.modify(message.payload)
        return keyword.value
    
    def handle_update(self, message):
        """Handle an update command."""
        message.verify(self.service)
        keyword = self.service[message.keyword]
        return keyword.update()
        
    def handle_identify(self, message):
        """Handle an identify command."""
        message.verify(self.service)
        if message.payload not in self.service:
            self.log.log(5, "Not identifying b/c not in service.")
            return FRAMEBLANK
        # This seems harsh, not using "CONTAINS", etc,
        # but it handles dispatchers correctly.
        try:
            kwd = self.service[message.payload]
        except WrongDispatcher:
            self.log.log(5, "Not identifying b/c wrong dispatcher.")
            return FRAMEBLANK
        else:
            ktl_type = kwd.KTL_TYPE
            if ktl_type is None:
                ktl_type = "basic"
            return ktl_type
        
    def handle_enumerate(self, message):
        """Handle enumerate command."""
        message.verify(self.service)
        return ":".join(self.service.keywords())
        
    def handle_broadcast(self, message):
        """Handle the broadcast command."""
        message.verify(self.service)
        message = ZMQCauldronMessage(command="broadcast", service=self.service.name, dispatcher=self.service.dispatcher, keyword=message.keyword, payload=message.payload, direction="CDB")
        socket = self._get_broadcaster()
        self.log.log(5, "Broadcast {0!s}".format(message))
        socket.send_multipart(message.data)
        return "success"
        
    def handle_heartbeat(self, message):
        """Heartbeat command does pretty much nothing."""
        self.log.log(5, "Heartbeat {0!s}".format(message))
        return "{0:.1f}".format(time.time())
        
        
    def connect(self):
        """Connect, and add a broadcaster."""
        self._get_broadcaster(wait=False)
        return super(_ZMQResponder, self).connect()
    
    def _get_broadcaster(self, wait=True):
        """Connect the broadcast socket."""
        zmq = check_zmq()
        if self._socket is not None:
            return self._socket
        self._socket = self.ctx.socket(zmq.PUB)
        try:
            address = zmq_get_address(self.service._config, "publish", bind=False)
            self._socket.connect(address)
        except zmq.ZMQError as e:
            self.log.error("Service can't connect to broadcaster address '{0}' because {1}".format(address, e))
            self._error = e
            raise
        else:
            self.log.log(5, "Broadcaster connected to {0}".format(address))
            if wait:
                time.sleep(0.2)
            return self._socket
    


@registry.dispatcher.service_for("zmq")
class Service(DispatcherService):
    """A ZMQ-based service."""
    def __init__(self, name, config, setup=None, dispatcher=None):
        zmq = check_zmq()
        self.ctx = zmq.Context.instance()
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
        
        zmq_connect_socket(socket, self._config, "broker", log=self.log, label='dispatcher')
        self._sockets.socket = socket
        return socket
        
    def _prepare(self):
        """Begin this service."""
        self._thread = _ZMQResponder(self)
        self._message_queue = []
    
    def _begin(self):
        """Allow command responses to start."""
        
        if not self._thread.is_alive():
            self._thread.start()
            self.log.debug("Started ZMQ Responder Thread.")
            
        self._thread.check_alive(timeout=10)
        
        while len(self._message_queue):
            self.socket.send_multipart(self._message_queue.pop().data)
            response = ZMQCauldronMessage.parse(self.socket.recv_multipart())
            response.verify(self)
        
    def shutdown(self):
        """Shutdown this object."""
        zmq = check_zmq()
        if hasattr(self, '_thread') and self._thread.is_alive():
            self._thread.stop()
        
    def _synchronous_command(self, command, payload, keyword=None, timeout=None):
        """Execute a synchronous command."""
        message = ZMQCauldronMessage(command, service=self.name, dispatcher=self.dispatcher,
            keyword=keyword.name if keyword else FRAMEBLANK, payload=payload, direction="CDQ")
        if not self._thread.running.is_set():
            self.log.log(5, "Queue {0!s}".format(message))
            return self._message_queue.append(message)
        elif threading.current_thread() == self._thread:
            self.log.log(5, "Request-local {0!s}".format(message))
            response = self._thread.handle(message)
        else:
            self.log.log(5, "Request {0!s}".format(message))
            self.socket.send_multipart(message.data)
            if timeout:
                if not self.socket.poll(timeout * 1e3):
                    raise TimeoutError("Dispatcher timed out.")
            response = ZMQCauldronMessage.parse(self.socket.recv_multipart())
        response.verify(self)
        return response
        

@registry.dispatcher.keyword_for("zmq")
class Keyword(DispatcherKeyword):
    """A keyword object for ZMQ Cauldron backends."""
    
    def _broadcast(self, value):
        """Broadcast this keyword value."""
        self.service._synchronous_command("broadcast", value, self)
        