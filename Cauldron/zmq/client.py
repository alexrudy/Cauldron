# -*- coding: utf-8 -*-
"""
ZMQ Client Implementation
"""

from __future__ import absolute_import

import weakref
from ..base import ClientService, ClientKeyword
from ..exc import CauldronAPINotImplementedWarning, CauldronAPINotImplemented, DispatcherError
from .common import zmq_dispatcher_address, zmq_broadcaster_address, check_zmq, teardown, ZMQCauldronMessage
from .router import lookup
from .. import registry
from ..config import get_module_configuration

import six
import threading
import logging
import warnings

registry.client.teardown_for('zmq')(teardown)

class _ZMQMonitorThread(threading.Thread):
    """A monitoring thread for ZMQ-powered Services which listens for broadcasts."""
    def __init__(self, service):
        super(_ZMQMonitorThread, self).__init__()
        self.service = weakref.proxy(service)
        self.shutdown = threading.Event()
        self.log = logging.getLogger("KTL.Service.Broadcasts")
        self.monitored = set()
        self.daemon = True
        
    def run(self):
        """Run the monitoring thread."""
        zmq = check_zmq()
        ctx = self.service.ctx
        socket = ctx.socket(zmq.SUB)
        try:
            socket.connect(zmq_broadcaster_address(self.service._config))
        
            # Accept everything belonging to this service.
            socket.setsockopt_string(zmq.SUBSCRIBE, six.text_type("broadcast:{0}".format(self.service.name)))
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
        except (zmq.ContextTerminated, zmq.ZMQError) as e:
            self.log.info("Service shutdown and context terminated, closing broadcast thread.")
        socket.close()

@registry.client.service_for("zmq")
class Service(ClientService):
    """Client service object for use with ZMQ."""
    
    def __init__(self, name, populate=False):
        zmq = check_zmq()
        self.ctx = zmq.Context.instance()
        self._socket = self.ctx.socket(zmq.REQ)
        self._config = get_module_configuration()
        self._thread = _ZMQMonitorThread(self)
        super(Service, self).__init__(name, populate)
        
    def _prepare(self):
        """Prepare step."""
        lookup(self)
        self._socket.connect(zmq_dispatcher_address(self._config))
        self._thread.start()
        
        
    def shutdown(self):
        """When this client is shutdown, close the subscription thread."""
        if hasattr(self, '_thread'):
            self._thread.shutdown.set()
        zmq = check_zmq()
        try:
            self._socket.close()
        except zmq.ZMQError as e:
            pass
        
    def has_keyword(self, name):
        """Check if a dispatcher has a keyword."""
        message = self._synchronous_command("identify", name, None)
        return message.payload == "yes"
        
    def keywords(self):
        """List all available keywords."""
        message = self._synchronous_command("enumerate", "", None)
        return message.payload.split(":")
        
    def __missing__(self, key):
        """Populate and return a missing key."""
        keyword = self._keywords[key] = Keyword(self, key)
        return keyword
        
    def _synchronous_command(self, command, payload, keyword=None):
        """Execute a synchronous command."""
        self._socket.send(str(ZMQCauldronMessage(command, self, keyword, payload, "REQ")))
        #TODO: Use polling here to support timeouts.
        return ZMQCauldronMessage.parse(self._socket.recv(), self)
    
@registry.client.keyword_for("zmq")
class Keyword(ClientKeyword):
    """Client keyword object for use with ZMQ."""
    
    def _ktl_reads(self):
        """Is this keyword readable?"""
        return True
        
    def _ktl_writes(self):
        """Is this keyword writable?"""
        return True
        
    def _ktl_monitored(self):
        """Is this keyword monitored."""
        return self.name in self.service._thread.monitored
        
    def _synchronous_command(self, command, payload):
        """Exectue a synchronous command."""
        return self.service._synchronous_command(command, payload, self)
        
    def wait(self, timeout=None, operator=None, value=None, sequence=None, reset=False, case=False):
        raise CauldronAPINotImplemented("Asynchronous operations are not supported for Cauldron.zmq")
    
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
            warnings.warn("Cauldron.zmq doesn't support asynchronous reads.", CauldronAPINotImplementedWarning)
        
        message = self._synchronous_command("update", "")
        self._update(message.payload)
        return self._current_value(binary=binary, both=both)
        
    def write(self, value, wait=True, binary=False, timeout=None):
        """Write a value"""
        if not self['writes']:
            raise NotImplementedError("Keyword '{0}' does not support writes.".format(self.name))
        
        if not wait or timeout is not None:
            warnings.warn("Cauldron.zmq doesn't support asynchronous writes.", CauldronAPINotImplementedWarning)
            
        # User-facing convenience to make writes smoother.
        try:
            value = self.cast(value)
        except (TypeError, ValueError):
            pass
        message = self._synchronous_command("modify", value)
        
        