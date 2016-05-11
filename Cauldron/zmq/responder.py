# -*- coding: utf-8 -*-
"""
Implements the ZMQ Dispatcher responder worker pool.
"""

from .common import zmq_get_address, check_zmq, zmq_connect_socket
from .microservice import ZMQMicroservice, ZMQThread
from .protocol import ZMQCauldronMessage, FRAMEFAIL, FRAMEBLANK
from .broker import ZMQBroker
from ..exc import DispatcherError, WrongDispatcher, TimeoutError

import collections
import threading
import logging
import weakref
import six
import time
import sys, traceback
import binascii

__all__ = ['ZMQResponder', 'ZMQPooler']

def register_dispatcher(service, socket, poller=None, log=None, timeout=1.0, address=None):
    """Register a dispatcher, and possibly start an automatic broker."""
    zmq = check_zmq()
    b = None
    if not _register_dispatcher(service, socket, poller=poller, log=log, timeout=timeout):
        b = ZMQBroker.daemon(config = service._config)
        time.sleep(1.0)
        if address is None:
            address = zmq_get_address(service._config, "broker", bind=False)
        ZMQBroker.check(config = service._config)
        socket.disconnect(address)
        socket.connect(address)
        if not _register_dispatcher(service, socket, poller=poller, log=log, timeout=timeout):
            raise TimeoutError("Can't connect to broker in subprocess.")
            
    if log is None:
        log = logging.getLogger(__name__ + ".register_dispatcher")
    # Send a start of work message.
    ready = ZMQCauldronMessage(command="ready", direction="DBQ",
        service=service.name, dispatcher=service.dispatcher)
    socket.send(b"", flags=zmq.SNDMORE)
    socket.send_multipart(ready.data)
    log.log(5, "Sent broker a ready message: {0!s}.".format(ready))
    return b

def _register_dispatcher(service, socket, poller=None, log=None, timeout=1.0):
    """Check broker"""
    zmq = check_zmq()
    
    if log is None:
        log = logging.getLogger(__name__ + "._register_dispatcher")
    
    # Send a welcome message to register this dispatcher.
    welcome = ZMQCauldronMessage(command="welcome", direction="DBQ",
        service=service.name, dispatcher=service.dispatcher)
    
    socket.send(b"", flags=zmq.SNDMORE)
    socket.send_multipart(welcome.data)
    log.log(5, "register.send({0!s})".format(welcome))
    
    if poller is None:
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
    
    # Check that we got the welcome message.
    ready = dict(poller.poll(timeout=timeout * 1e3))
    if ready.get(socket) == zmq.POLLIN:
        message = ZMQCauldronMessage.parse(socket.recv_multipart())
        if message.payload != "confirmed":
            raise DispatcherError("Message confirming welcome was malformed! {0!s}".format(message))
        return True
    else:
        log.log(5, "register.timeout after {0} seconds.".format(timeout))
        return False
    

class ZMQPooler(ZMQThread):
    """A thread object for handling pools of ZMQ workers."""
    def __init__(self, service, frontend_address, pool_size=None, timeout=1):
        super(ZMQPooler, self).__init__(name="DFW.Service.{0}.Pool".format(service.name), context=service.ctx)
        self.service = weakref.proxy(service)
        self._backend_address = "inproc://{0}-backend".format(hex(id(self)))
        self._frontend_address = frontend_address
        self._worker_queue = collections.deque()
        self._workers = set()
        if pool_size is None:
            pool_size = self.service._config.getint("zmq", "pool")
        self._pool_size = pool_size
        self.timeout = timeout
        self.daemon = True
    
    def _poll_and_respond(self, poller, frontend, backend, signal):
        """Poll for messages, handle them."""
        zmq = check_zmq()
        ready = dict(poller.poll(timeout=self.timeout*1e3))
        if not (self.running.isSet() or len(ready)):
            return False
        if signal in ready:
            _ = signal.recv()
            self.log.log(5, "Got a signal: .running = {0}".format(self.running.is_set()))
            return True
        if backend in ready:
            identifier = backend.recv()
            _ = backend.recv()
            msg = backend.recv_multipart()
            self._worker_queue.append(identifier)
            if len(msg) == 1 and msg[0] == b"ready":
                self.log.log(5, "{0}.recv() worker {1} ready".format(self, binascii.hexlify(identifier)))
            else:
                self.log.log(5, "{0}.broker() B2F {1}".format(self, binascii.hexlify(identifier)))
                frontend.send(b"", flags=zmq.SNDMORE)
                frontend.send_multipart(msg)
        if frontend in ready and len(self._worker_queue):
            _ = frontend.recv()
            msg = frontend.recv_multipart()
            if self.running.isSet():
                worker = self._worker_queue.popleft()
                self.log.log(5, "{0}.broker() F2B {1}".format(self, binascii.hexlify(worker)))
                backend.send(worker, flags=zmq.SNDMORE)
                backend.send(b"", flags=zmq.SNDMORE)
                backend.send_multipart(msg)
            else:
                try:
                    response = ZMQCauldronMessage.parse(msg).error_response("Dispatcher shutdown.")
                except Exception:
                    pass
                else:
                    frontend.send(b"", flags=zmq.SNDMORE)
                    frontend.send_multipart(response.data)
        return True
    
    def main(self):
        """Run the thread worker"""
        zmq = check_zmq()
        signal = self.get_signal_socket()
        
        frontend = self.ctx.socket(zmq.DEALER)
        self.connect(frontend, self._frontend_address)
        backend = self.ctx.socket(zmq.ROUTER)
        self.connect(backend, self._backend_address, 'bind')
        
        poller = zmq.Poller()
        poller.register(frontend, zmq.POLLIN)
        poller.register(backend, zmq.POLLIN)
        poller.register(signal, zmq.POLLIN)
        
        self.__broker = register_dispatcher(self.service, frontend, poller, self.log, address=self._frontend_address)
        
        self.log.debug("{0} starting workers".format(self))
        for i in range(self._pool_size):
            worker = ZMQWorker(self.service, self._backend_address, n=i)
            self._workers.add(worker)
            worker.start()
        
        self.log.debug("{0}.running".format(self))
        self.started.set()
        try:
            while self.running.is_set():
                if not self._poll_and_respond(poller, frontend, backend, signal):
                    break
        finally:
            for worker in self._workers:
                worker.stop()
            for worker in self._workers:
                worker.join()
            self.log.debug("Done with workers.")
            backend.close()
            frontend.close()
            signal.close()
        
    def __del__(self):
        """Stop workers when we delete this."""
        self.running.clear()
        for worker in self._workers:
            worker.stop()

class ZMQWorker(ZMQMicroservice):
    """A ZMQ-based worker"""
    
    def __init__(self, service, address=None, n=0):
        self.service = service
        if address is None:
            address = zmq_get_address(self.service._config, "broker", bind=False)
        super(ZMQWorker, self).__init__(address=address,
            context=self.service.ctx, name="DFW.Service.{0:s}.Responder.{1:d}".format(self.service.name,n))
        self._broadcaster = None
        self.daemon = True
        
    def handle_modify(self, message):
        """Handle a modify command."""
        message.verify(self.service)
        keyword = self.service[message.keyword]
        with keyword._lock:
            keyword.modify(message.payload)
        return keyword.value
    
    def handle_update(self, message):
        """Handle an update command."""
        message.verify(self.service)
        keyword = self.service[message.keyword]
        with keyword._lock:
            value = keyword.update()
        return value
        
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
        self.log.log(5, "{0!r}.broadcast({1!s})".format(self, message))
        self._broadcaster.send_multipart(message.data)
        return "success"
        
    def handle_heartbeat(self, message):
        """Heartbeat command does pretty much nothing."""
        self.log.log(5, "{0!r}.beat({1!s})".format(self, message))
        return "{0:.1f}".format(time.time())
        
    def respond(self):
        """Call the responder loop, the main function for this thread."""
        zmq = check_zmq()
        signal = self.get_signal_socket()
        
        backend = self.ctx.socket(zmq.DEALER)
        self.connect(backend, self.address)
        
        broadcaster = self.ctx.socket(zmq.PUB)
        self.connect(broadcaster, zmq_get_address(self.service._config, "publish", bind=False))
        
        self._broadcaster = broadcaster
        
        poller = zmq.Poller()
        poller.register(backend, zmq.POLLIN)
        poller.register(signal, zmq.POLLIN)
        
        backend.send_multipart([b"", b"ready"])
        
        self.started.set()
        self.log.log(5, "Starting responder loop.")
        while self.running.is_set():
            ready = dict(poller.poll(timeout=self.timeout*1e3))
            if signal in ready:
                _ = signal.recv()
                self.log.log(5, "Got a signal: .running = {0}".format(self.running.is_set()))
                continue
            if backend in ready:
                message = ZMQCauldronMessage.parse(backend.recv_multipart())
                self.log.log(5, "{0!r}.recv({1})".format(self, message))
                response = self.handle(message)
                self.log.log(5, "{0!r}.send({1})".format(self, response))
                backend.send_multipart(response.data)

        
        backend.close()
        signal.close()
    

