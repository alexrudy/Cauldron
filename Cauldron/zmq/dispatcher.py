# -*- coding: utf-8 -*-
"""
Dispatcher implementation for ZMQ

"""

from .common import zmq_get_address, check_zmq, teardown, zmq_connect_socket
from .protocol import ZMQCauldronMessage, FRAMEFAIL, FRAMEBLANK
from .responder import ZMQPooler
from .broker import ZMQBroker
from .schedule import ZMQScheduler
from .tasker import Task, TaskQueue
from ..base import DispatcherService, DispatcherKeyword
from .. import registry
from ..exc import DispatcherError, WrongDispatcher, TimeoutError

import threading
import logging
import weakref
import six
import time
import sys, traceback
import atexit

__all__ = ["Service", "Keyword"]

def teardown():
    """Teardown registered instances."""
    _cleanup()

registry.dispatcher.teardown_for('zmq')(teardown)

_service_registry = set()

def _cleanup(_registry=_service_registry):
    """Cleanup a service instance at exit."""
    while True:
        try:
            svc = _registry.pop()
        except KeyError:
            break
        else:
            svc.shutdown()

atexit.register(_cleanup)

@registry.dispatcher.service_for("zmq")
class Service(DispatcherService):
    # A ZMQ-based service.
    def __init__(self, name, config, setup=None, dispatcher=None):
        zmq = check_zmq()
        self.ctx = zmq.Context.instance()
        self._sockets = threading.local()
        self._sockets_to_close = set()
        self._alive = False
        _service_registry.add(self)
        super(Service, self).__init__(name, config, setup, dispatcher)
        
    @property
    def socket(self):
        """A thread-local ZMQ socket for sending commands to the responder thread."""
        # Short out if we already have a socket.
        if hasattr(self._sockets, 'socket'):
            return self._sockets.socket
        
        zmq = check_zmq()
        socket = self.ctx.socket(zmq.DEALER)
        
        zmq_connect_socket(socket, self._config, "broker", log=self.log, label='dispatcher')
        self._sockets.socket = socket
        self._sockets_to_close.add(socket)
        return socket
        
    def _prepare(self):
        """Begin this service."""
        self._worker_pool = ZMQPooler(self, zmq_get_address(self._config, "broker", bind=False))
        self._tasker = TaskQueue(self.log.name +".Tasks", ctx=self.ctx, 
                                 log=self.log, backend_address=self._worker_pool.internal_address)
        self._scheduler = ZMQScheduler(self.log.name + ".Scheduler", self.ctx)
    
    def _begin(self):
        """Allow command responses to start."""
        zmq = check_zmq()
        try:
            if not self._worker_pool.is_alive():
                self._worker_pool.start()
                self.log.trace("Started ZMQ Responder Thread.")
            if not self._scheduler.is_alive():
                self._scheduler.start()
                self.log.trace("Started ZMQ Scheduler Thread.")
            if not self._tasker.is_alive():
                self._tasker.start()
                self.log.trace("Started ZMQ Tasker Thread.")
            
            self._worker_pool.check(timeout=10)
            self._scheduler.check(timeout=10)
            self._tasker.check(timeout=10)
        except:
            self._worker_pool.stop()
            self._scheduler.stop()
            raise
        else:
            self._alive = True
        
    def shutdown(self):
        
        # The following block tries to get around
        # a few race conditions which can happen
        # when shutting down a service explicitly.
        
        # This code is unlikely to matter in real
        # world cases. It works by giving up the
        # GIL for a short amount of time if it
        # detects a locked keyword. Keywords are
        # only locked by the underlying responder
        # threads which handle KTL commands.
        for keyword in self._keywords.values():
            try:
                if keyword._lock.acquire(False):
                    keyword._lock.release()
                else:
                    time.sleep(0.1)
                    break
            except:
                pass
        
        if hasattr(self, '_tasker') and self._tasker is not None and self._tasker.is_alive():
            self._tasker.stop()
        
        if hasattr(self, '_scheduler') and self._scheduler is not None and self._scheduler.is_alive():
            self._scheduler.stop()
        
        if hasattr(self, '_worker_pool') and self._worker_pool is not None and self._worker_pool.is_alive():
            self._worker_pool.stop()
        
        for socket in self._sockets_to_close:
            socket.close()
        try:
            # Crazy things can happen atexit, so don't worry about this.
            _service_registry.discard(self)
        except:
            pass
        self._alive = False
        
    def _asynchronous_command(self, command, payload, keyword=None, timeout=None, callback=None):
        """Execute a synchronous command."""
        return self._tasker.asynchronous_command(command, payload, self, keyword, direction="CDQ",
                                                 timeout=timeout, callback=callback,
                                                 dispatcher=self.dispatcher)
        
    def _synchronous_command(self, command, payload, keyword=None, timeout=None, callback=None):
        """Handle synchronous command."""
        return self._tasker.synchronous_command(command, payload, self, keyword, direction="CDQ",
                                                timeout=timeout, callback=callback,
                                                dispatcher=self.dispatcher)
        

@registry.dispatcher.keyword_for("zmq")
class Keyword(DispatcherKeyword):
    # A keyword object for ZMQ Cauldron backends.
    
    def __init__(self, name, service, initial=None, period=None):
        super(Keyword, self).__init__(name, service, initial=initial, period=period)
    
    def _broadcast(self, value):
        """Broadcast this keyword value."""
        self.service._asynchronous_command("broadcast", value, self.name)
        self.log.trace("{0!r}.broadcast() done.".format(self))
    
    def schedule(self, appointment=None, cancel=False):
        """Schedule an update."""
        if cancel:
            self.service._scheduler.cancel_appointment(appointment, self)
        else:
            self.service._scheduler.appointment(appointment, self)
    
    
    def period(self, period):
        """How often a keyword should be updated."""
        self.service._scheduler.period(period, self)
        