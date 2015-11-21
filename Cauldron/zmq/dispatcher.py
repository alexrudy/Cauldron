# -*- coding: utf-8 -*-
"""
Dispatcher implementation for ZMQ

"""

from .common import zmq_dispatcher_address, zmq_broadcaster_address, check_zmq, teardown
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
                message = socket.recv()
                cmd, service, kwd, value = message.split(":", 3)
                if kwd == "":
                    keyword = None
                else:
                    try:
                        keyword = self.service[kwd]
                    except KeyError:
                        message = "Bad request, invalid keyword '{0:s}'".format(kwd)
                        self.log.error(message)
                        socket.send("{0}Error:{1}:{2}".format(cmd, service, kwd, message))
                try:
                    if cmd == 'modify':
                        resp = keyword.modify(value)
                    elif cmd == 'update':
                        resp = keyword.update()
                    elif cmd == "identify":
                        # If we are here, and the command is identify, 
                        # we can return 'yes', because we already checked for
                        # the existence of the keyword above.
                        resp = "yes" if value in self.service else "no"
                    elif cmd == "enumerate":
                        resp = ":".join(self.service.keywords())
                except Exception as e:
                    socket.send("{0}Error:{1}:{2}:{3}".format(cmd, service, kwd, repr(e)))
                    self.log.error(repr(e))
                else:
                    socket.send("{0}:{1}:{2}:{3}".format(cmd, service, kwd, resp))
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
        self._broadcast_socket.close()
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
        
        