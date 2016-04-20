# -*- coding: utf-8 -*-
"""
Dispatcher implementation for ZMQ

"""

from .common import zmq_get_address, check_zmq, teardown, zmq_connect_socket
from .protocol import ZMQCauldronMessage, FRAMEFAIL, FRAMEBLANK
from .responder import ZMQPooler
from .broker import ZMQBroker
from .schedule import Scheduler
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

@registry.dispatcher.service_for("zmq")
class Service(DispatcherService):
    # A ZMQ-based service.
    def __init__(self, name, config, setup=None, dispatcher=None):
        zmq = check_zmq()
        self.ctx = zmq.Context.instance()
        self._sockets = threading.local()
        self._sockets_to_close = set()
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
        self._sockets_to_close.add(socket)
        return socket
        
    def _prepare(self):
        """Begin this service."""
        self._thread = ZMQPooler(self, zmq_get_address(self._config, "broker", bind=False))
        self._scheduler = Scheduler(self.log.name + ".Scheduler", self.ctx)
        self._message_queue = []
    
    def _begin(self):
        """Allow command responses to start."""
        
        if not self._thread.is_alive():
            self._thread.start()
            self.log.debug("Started ZMQ Responder Thread.")
            
        if not self._scheduler.is_alive():
            self._scheduler.start()
            self.log.debug("Started ZMQ Scheduler Thread.")
            
        self._thread.check(timeout=10)
        self._scheduler.check(timeout=10)
        
        while len(self._message_queue):
            self.socket.send_multipart(self._message_queue.pop().data)
            response = ZMQCauldronMessage.parse(self.socket.recv_multipart())
            response.verify(self)
        
    def shutdown(self):
        if hasattr(self, '_scheduler') and self._scheduler.is_alive():
            self._scheduler.stop()
            self._scheduler.join()
        
        if hasattr(self, '_thread') and self._thread.is_alive():
            self._thread.stop()
            self._thread.join()
        
        for socket in self._sockets_to_close:
            socket.close()
        
    def _synchronous_command(self, command, payload, keyword=None, timeout=None):
        """Execute a synchronous command."""
        message = ZMQCauldronMessage(command, service=self.name, dispatcher=self.dispatcher,
            keyword=keyword.name if keyword else FRAMEBLANK, payload=payload, direction="CDQ")
        if not self._thread.running.is_set():
            self.log.log(5, "{0!r}.queue({1!s})".format(self, message))
            return self._message_queue.append(message)
        else:
            self.log.log(5, "{0!r}.send({0!s})".format(message))
            self.socket.send_multipart(message.data)
            if timeout:
                if not self.socket.poll(timeout * 1e3):
                    raise TimeoutError("Dispatcher timed out.")
            response = ZMQCauldronMessage.parse(self.socket.recv_multipart())
        response.verify(self)
        return response
        

@registry.dispatcher.keyword_for("zmq")
class Keyword(DispatcherKeyword):
    # A keyword object for ZMQ Cauldron backends.
    
    def __init__(self, name, service, initial=None, period=None):
        super(Keyword, self).__init__(name, service, initial=initial, period=period)
        self._lock = threading.RLock()
    
    def _broadcast(self, value):
        """Broadcast this keyword value."""
        self.service._synchronous_command("broadcast", value, self)
    
    def schedule(self, appointment=None, cancel=False):
        """Schedule an update."""
        if cancel:
            self.service._scheduler.cancel_appointment(appointment, self)
        else:
            self.service._scheduler.appointment(appointment, self)
    
    
    def period(self, period):
        """How often a keyword should be updated."""
        self.service._scheduler.period(period, self)
        