# -*- coding: utf-8 -*-
"""
Dispatcher implementation for ZMQ

"""

from . import ZMQ_DISPATCHER_BIND, ZMQ_DISPATCHER_BROADCAST
from ..base import DispatcherService, DispatcherKeyword
from .. import registry

import threading
import logging
import weakref
import zmq

class _ZMQResponderThread(threading.Thread):
    """A python thread for ZMQ responses."""
    def __init__(self, service):
        super(_ZMQResponderThread, self).__init__()
        self._shutdown = threading.Event()
        self.service = weakref.proxy(service)
        self.log = logging.getLogger("DFW.Service.Thread")
    
    def run(self):
        """Run the thread."""
        ctx = zmq.Context.instance()
        socket = ctx.socket(zmq.REP)
        socket.bind(ZMQ_DISPATCHER_BIND)
        try:
            while not self._shutdown.isSet():
                message = socket.recv()
                cmd, service, kwd, value = message.split(":", 3)
                try:
                    keyword = self.service[kwd]
                except KeyError:
                    self.log.error("Bad request, invalid keyword {0:s}".format(kwd))
                try:
                    if cmd == 'modify':
                        resp = keyword.modify(value)
                    elif cmd == 'update':
                        resp = keyword.update()
                except Exception as e:
                    socket.send("{0}Error:{1}:{2}".format(cmd, service, repr(e)))
                    self.log.error(repr(e))
                else:
                    socket.send("{0}:{1}:{2}".format(cmd, service, resp))
        except weakref.ReferenceError as e:
            self.log.error("Service reference error, {0}".format(repr(e)))
        return
        
    
    def stop(self):
        """Stop the responder thread."""
        self._shutdown.set()
    


@registry.dispatcher.service_for("zmq")
class Service(DispatcherService):
    """A ZMQ-based service."""
    def __init__(self, name, config, setup, dispatcher):
        super(Service, self).__init__(name, config, setup, dispatcher)
        self.ctx = zmq.Context.instance()
        self._broadcast_socket = self.ctx.socket(zmq.PUB)
        self._broadcast_socket.bind(ZMQ_DISPATCHER_BROADCAST)
        self._thread = _ZMQResponderThread(self)
        
    def _begin(self):
        """Begin this service."""
        self._thread.start()
        
    def shutdown(self):
        """Shutdown this object."""
        if hasattr(self, '_thread') and self._thread.isAlive():
            self._thread.stop()
        
    def __missing__(self, key):
        """Allows the redis dispatcher to populate any keyword, whether it should exist or not."""
        return Keyword(key, self)
        

@registry.dispatcher.keyword_for("zmq")
class Keyword(DispatcherKeyword):
    """A keyword object for ZMQ Cauldron backends."""
    
    def _broadcast(self, value):
        """Broadcast this keyword value."""
        self.service._broadcast_socket.send("broadcast:{0}:{1}:{2}".format(self.service.name, self.name, value))
        
        