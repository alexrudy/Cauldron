# -*- coding: utf-8 -*-
"""
ZMQ Client Implementation
"""

from __future__ import absolute_import

import weakref
from ..base import ClientService, ClientKeyword
from ..exc import CauldronAPINotImplementedWarning, CauldronAPINotImplemented, DispatcherError
from . import zmq_dispatcher_address, zmq_broadcaster_address
from .. import registry
import zmq
import threading
import logging

class _ZMQMonitorThread(threading.Thread):
    """docstring for _ZMQMonitorThread"""
    def __init__(self, service):
        super(_ZMQMonitorThread, self).__init__()
        self.service = weakref.proxy(service)
        self.shutdown = threading.Event()
        self.log = logging.getLogger("KTL.Service.Thread")
        self.monitored = set()
        
    def run(self):
        """Run the monitoring thread."""
        ctx = zmq.Context.instance()
        socket = ctx.socket(zmq.SUB)
        socket.connect(zmq_broadcaster_address())
        
        # Accept everything belonging to this service.
        socket.setsockopt_string(zmq.SUBSCRIBE, "broadcast:{0}".format(self.service.name))
        
        while not self.shutdown.isSet():
            if socket.poll(timeout=1.0):
                message = socket.recv()
                cmd, service, kwd, value = message.split(":", 3)
                if kwd in self.monitored:
                    try:
                        keyword = self.service[kwd]
                    except KeyError:
                        self.log.error("Bad request, invalid keyword {0:s}".format(kwd))
                    keyword._update(value)

@registry.client.service_for("zmq")
class Service(ClientService):
    """Client service object for use with ZMQ."""
    
    def __init__(self, name, populate=False):
        super(Service, self).__init__(name, populate)
        self.ctx = zmq.Context.instance()
        self._socket = zmq.socket(zmq.REQ)
        self._socket.connect(zmq_dispatcher_address())
        self._thread = _ZMQMonitorThread(self)
        self._thread.start()
        
    def shutdown(self):
        """When this client is shutdown, close the subscription thread."""
        self._thread.shutdown.set()
        self._thread.join()
    
@registry.client.keyword_for("zmq")
class Keyword(ClientKeyword):
    """Client keyword object for use with ZMQ."""
    
    def _ktl_reads(self):
        """Is this keyword readable?"""
        return True
        
    def _ktl_writes(self):
        """Is this keyword writable?"""
        return True
    
    def monitor(self, start=True, prime=True, wait=True):
        if prime:
            self.read(wait=wait)
        if start:
            self.service._thread.monitored.add(self.name)
        else:
            self.service._thread.monitored.remove(self.name)
    
    def read(self, binary=False, both=False, wait=True, timeout=None):
        """Read a value, synchronously, always."""
        
        if not self['reads']:
            raise NotImplementedError("Keyword '{0}' does not support reads.".format(self.name))
        
        if not wait or timeout is not None:
            warnings.warn("Cauldron.redis doesn't support asynchronous reads.", CauldronAPINotImplementedWarning)
        
        self.service.socket.send("update:{0}:{1}:".format(self.service.name, self.name))
        message = self.service.socket.recv()
        cmd, service, response = message.split(":",3)
        if "Error" in cmd:
            raise DispatcherError(response)
        self._update(response)
        return self._current_value(binary=binary, both=both)
        
    def write(self, value, wait=True, binary=False, timeout=None):
        """Write a value"""
        if not self['writes']:
            raise NotImplementedError("Keyword '{0}' does not support writes.".format(self.name))
        
        if not wait or timeout is not None:
            warnings.warn("Cauldron.redis doesn't support asynchronous writes.", CauldronAPINotImplementedWarning)
            
        # User-facing convenience to make writes smoother.
        try:
            value = self.cast(value)
        except (TypeError, ValueError):
            pass
        
        self.service.socket.send("modify:{0}:{1}:{2}".format(self.service.name, self.name, value))
        message = self.service.socket.recv()
        cmd, service, response = message.split(":",3)
        if "Error" in cmd:
            raise DispatcherError(response)
        