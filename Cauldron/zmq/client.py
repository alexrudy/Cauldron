# -*- coding: utf-8 -*-
"""
ZMQ Client Implementation
"""

from __future__ import absolute_import

import weakref
from ..base import ClientService, ClientKeyword
from ..exc import CauldronAPINotImplementedWarning, CauldronAPINotImplemented, DispatcherError, TimeoutError
from .common import zmq_dispatcher_address, zmq_broadcaster_address, check_zmq, teardown, zmq_address
from .microservice import ZMQCauldronMessage, ZMQCauldronErrorResponse, FRAMEBLANK, FRAMEFAIL
from .. import registry
from ..config import cauldron_configuration

import six
import threading
import logging
import warnings

__all__ = ["Service", "Keyword"]

registry.client.teardown_for('zmq')(teardown)

class _ZMQMonitorThread(threading.Thread):
    """A monitoring thread for ZMQ-powered Services which listens for broadcasts."""
    def __init__(self, service):
        super(_ZMQMonitorThread, self).__init__()
        self.service = weakref.proxy(service)
        self.shutdown = threading.Event()
        self.log = logging.getLogger("ktl.Service.{0}.Broadcasts".format(service.name))
        self.monitored = set()
        self.daemon = True
        
    def run(self):
        """Run the monitoring thread."""
        zmq = check_zmq()
        try:
            ctx = self.service.ctx
        except weakref.ReferenceError:
            self.log.log(5, "Can't start ZMQ monitor, service has disappeared.")
            return
        socket = ctx.socket(zmq.SUB)
        try:
            address = zmq_address(self.service._config, "broadcast", bind=False)
            socket.connect(address)
        
            # Accept everything belonging to this service.
            socket.setsockopt_string(zmq.SUBSCRIBE, six.text_type(self.service.name))
            self.log.log(5, "Started Monitor Thread for {0}".format(address))
            while not self.shutdown.isSet():
                if socket.poll(timeout=0.1):
                    try:
                        message = ZMQCauldronMessage.parse(socket.recv_multipart())
                        message.verify(self.service)
                        keyword = self.service[message.keyword]
                        if keyword.name in self.monitored:
                            keyword._update(message.payload)
                            self.log.log(5, "Accepted broadcast for {0}: {1}".format(keyword.name, message.payload))
                        else:
                            self.log.log(5, "Ignored broadcast for {0}, not monitored.".format(keyword.name))
                    except ZMQCauldronErrorResponse as e:
                        self.log.error("Broadcast Message Error: {0!r}".format(e))
                    except (zmq.ContextTerminated, zmq.ZMQError):
                        raise
                    except Exception as e:
                        self.log.error("Broadcast Error: {0!r}".format(e))
        except (zmq.ContextTerminated, zmq.ZMQError) as e:
            self.log.info("Service shutdown and context terminated, closing broadcast thread.")
        else:
            try:
                socket.setsockopt(zmq.LINGER, 0)
                socket.close()
            except:
                pass
        finally:
            self.log.log(5, "Stopping Monitor Thread")
            

@registry.client.service_for("zmq")
class Service(ClientService):
    """Client service object for use with ZMQ."""
    
    def __init__(self, name, populate=False):
        zmq = check_zmq()
        self.ctx = zmq.Context.instance()
        self._sockets = threading.local()
        self._config = cauldron_configuration
        self._thread = None
        self._lock = threading.RLock()
        self._type_ktl_cache = {}
        super(Service, self).__init__(name, populate)
        
    @property
    def socket(self):
        """A thread-local ZMQ socket for sending commands to the responder thread."""
        # Short out if we already have a socket.
        if hasattr(self._sockets, 'socket'):
            return self._sockets.socket
        
        zmq = check_zmq()
        socket = self.ctx.socket(zmq.REQ)
        try:
            address = zmq_address(self._config, "broker")
            socket.connect(address)
        except zmq.ZMQError as e:
            self.log.error("Service can't connect to responder address '{0}' because {1}".format(address, e))
            raise
        else:
            self.log.debug("Connected client to {0}".format(address))
            self._sockets.socket = socket
        return socket
        
    def _prepare(self):
        """Prepare step."""
        self._thread = _ZMQMonitorThread(self)
        address = self._synchronous_command("lookup", "subscribe", direction="CBQ").payload
        self._thread.address = address
        self._thread.start()
        
    def _ktl_type(self, key):
        """Get the KTL type of a specific keyword."""
        name = key.upper()
        with self._lock:
            if name in self._type_ktl_cache:
                return self._type_ktl_cache[name]
            message = self._synchronous_command("identify", payload=name, keyword=name, direction="CSQ")
            items = list(set(message.payload.split(":")))
            if len(items) == 1 and (items[0] not in (FRAMEBLANK, FRAMEFAIL)):
                ktl_type = items[0]
            else:
                raise KeyError("Keyword '{0}' does not exist.".format(name))
            self._type_ktl_cache[name] = ktl_type
            return ktl_type
        
    def shutdown(self):
        """When this client is shutdown, close the subscription thread."""
        if hasattr(self, '_thread'):
            self._thread.shutdown.set()
        
    def has_keyword(self, name):
        """Check if a dispatcher has a keyword."""
        assert name.upper() != self.name.upper()
        name = name.upper()
        try:
            ktype = self._ktl_type(name)
        except KeyError as e:
            return False
        else:
            return True
        
    def keywords(self):
        """List all available keywords."""
        message = self._synchronous_command("enumerate", FRAMEBLANK, direction="CSQ")
        return message.payload.split(":")
        
    def _synchronous_command(self, command, payload, keyword=None, direction="CDQ", timeout=None):
        """Execute a synchronous command."""
        request = ZMQCauldronMessage(command, direction=direction,
            service=self.name, dispatcher=FRAMEBLANK,
            keyword=keyword if keyword else FRAMEBLANK, 
            payload=payload if payload else FRAMEBLANK)
        self.log.log(5, "{0!r}.send({1!s})".format(self, request))
        self.socket.send_multipart(request.data)
        
        if timeout:
            if not self.socket.poll(timeout * 1e3):
                raise TimeoutError("Dispatcher timed out.")
        
        message = ZMQCauldronMessage.parse(self.socket.recv_multipart())
        self.log.log(5, "{0!r}.recv({1!s})".format(self, message))
        if message.iserror:
            raise DispatcherError("Dispatcher error on command: {0}".format(message.payload))
        message.verify(self)
        return message
    
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
        
    def _synchronous_command(self, command, payload, timeout=None):
        """Execute a synchronous command."""
        return self.service._synchronous_command(command, payload, self.name, timeout=timeout)
        
    def wait(self, timeout=None, operator=None, value=None, sequence=None, reset=False, case=False):
        raise CauldronAPINotImplemented("Asynchronous operations are not supported for Cauldron.zmq")
    
    def monitor(self, start=True, prime=True, wait=True):
        if start:
            if prime:
                self.read(wait=wait)
            self.service._thread.monitored.add(self.name)
        else:
            self.service._thread.monitored.remove(self.name)
    
    def read(self, binary=False, both=False, wait=True, timeout=None):
        """Read a value, synchronously, always."""
        
        if not self['reads']:
            raise NotImplementedError("Keyword '{0}' does not support reads.".format(self.name))
        
        if not wait or timeout is not None:
            warnings.warn("Cauldron.zmq doesn't support asynchronous reads.", CauldronAPINotImplementedWarning)
        
        message = self._synchronous_command("update", "", timeout=timeout)
        self._update(message.payload)
        return self._current_value(binary=binary, both=both)
        
    def write(self, value, wait=True, binary=False, timeout=None):
        """Write a value"""
        if not self['writes']:
            raise NotImplementedError("Keyword '{0}' does not support writes.".format(self.name))
        
        if not wait:
            warnings.warn("Cauldron.zmq doesn't support asynchronous writes.", CauldronAPINotImplementedWarning)
            
        # User-facing convenience to make writes smoother.
        try:
            value = self.cast(value)
        except (TypeError, ValueError):
            pass
        message = self._synchronous_command("modify", value, timeout=timeout)
        
        