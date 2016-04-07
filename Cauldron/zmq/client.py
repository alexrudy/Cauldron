# -*- coding: utf-8 -*-
"""
ZMQ Client Implementation
"""

from __future__ import absolute_import

import weakref
from ..base import ClientService, ClientKeyword
from ..exc import CauldronAPINotImplementedWarning, CauldronAPINotImplemented, DispatcherError, TimeoutError
from .common import zmq_get_address, check_zmq, teardown, zmq_connect_socket
from .microservice import ZMQCauldronMessage, ZMQCauldronErrorResponse, FRAMEBLANK, FRAMEFAIL
from .tasker import Task, TaskQueue
from .. import registry
from ..config import get_configuration, get_timeout

import six
import threading
import logging
import warnings

__all__ = ["Service", "Keyword"]

registry.client.teardown_for('zmq')(teardown)

class _ZMQMonitorThread(threading.Thread):
    """A monitoring thread for ZMQ-powered Services which listens for broadcasts."""
    def __init__(self, service):
        super(_ZMQMonitorThread, self).__init__(name="ktl.Service.{0}.Broadcasts".format(service.name))
        self.service = weakref.proxy(service)
        self.shutdown = threading.Event()
        self.log = logging.getLogger(self.name)
        self.monitored = set()
        self.daemon = True
        self.address = None
        
    def stop(self):
        """Stop this thread."""
        self.shutdown.set()
        if not self.isAlive():
            return
        self.log.debug("Joining {0}".format(self.name))
        self.join()
        
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
            zmq_connect_socket(socket, get_configuration(), "subscribe", log=self.log, label='client-monitor', address=self.address)
            # Accept everything belonging to this service.
            socket.setsockopt_string(zmq.SUBSCRIBE, six.text_type(self.service.name))
            
            while not self.shutdown.isSet():
                if socket.poll(timeout=1):
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
            self.log.log(6, "Service shutdown and context terminated, closing broadcast thread. {0}".format(repr(e)))
        else:
            try:
                socket.setsockopt(zmq.LINGER, 0)
                socket.close()
            except:
                pass
        finally:
            self.log.debug("Stopped Monitor Thread")
            

@registry.client.service_for("zmq")
class Service(ClientService):
    # Client service object for use with ZMQ.
    
    def __init__(self, name, populate=False):
        zmq = check_zmq()
        self.ctx = zmq.Context.instance()
        self._sockets = threading.local()
        self._monitor = None
        self._tasker = None
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
        zmq_connect_socket(socket, get_configuration(), "broker", log=self.log, label='client')
        self._sockets.socket = socket
        return socket
        
    def _prepare(self):
        """Prepare step."""
        self._monitor = _ZMQMonitorThread(self)
        self._tasker = TaskQueue(self.name, ctx=self.ctx, log=self.log)
        self._tasker.start()
        address = self._synchronous_command("lookup", "subscribe", direction="CBQ")
        self._monitor.address = address
        self._monitor.start()
        
    def _ktl_type(self, key):
        """Get the KTL type of a specific keyword."""
        name = key.upper()
        with self._lock:
            if name in self._type_ktl_cache:
                return self._type_ktl_cache[name]
            message = self._synchronous_command("identify", payload=name, keyword=name, direction="CSQ")
            items = list(set(message.split(":")))
            if len(items) == 1 and (items[0] not in (FRAMEBLANK.decode('utf-8'), FRAMEFAIL.decode('utf-8'))):
                ktl_type = items[0]
            else:
                raise KeyError("Keyword '{0}' does not exist.".format(name))
            self._type_ktl_cache[name] = ktl_type
            return ktl_type
        
    def __del__(self):
        """On delete, try to shutdown."""
        self.shutdown()
        
    def shutdown(self):
        if hasattr(self, '_monitor'):
            self._monitor.stop()
        if hasattr(self, '_tasker'):
            self._tasker.stop()
        
    def has_keyword(self, name):
        assert name.upper() != self.name.upper()
        name = name.upper()
        try:
            ktype = self._ktl_type(name)
        except KeyError as e:
            return False
        else:
            return True
        
    def keywords(self):
        message = self._synchronous_command("enumerate", FRAMEBLANK, direction="CSQ")
        return message.split(":")
        
    def _handle_response(self, message):
        """Handle a response, and return the payload."""
        self.log.log(5, "{0!r}.recv({1!s})".format(self, message))
        if message.iserror:
            raise DispatcherError("Dispatcher error on command: {0}".format(message.payload))
        message.verify(self)
        return message.payload
    
    def _asynchronous_command(self, command, payload, keyword=None, direction="CDQ", timeout=None, callback=None):
        """Run an asynchronous command."""
        request = ZMQCauldronMessage(command, direction=direction,
            service=self.name, dispatcher=FRAMEBLANK,
            keyword=keyword if keyword else FRAMEBLANK, 
            payload=payload if payload else FRAMEBLANK)
        
        callback = callback or self._handle_response
        
        task = Task(request, callback, get_timeout(timeout))
        self._tasker.queue.put(task)
        return task
        
    def _synchronous_command(self, command, payload, keyword=None, direction="CDQ", timeout=None, callback=None):
        """Execute a synchronous command."""
        timeout = get_timeout(timeout)
        task = self._asynchronous_command(command, payload, keyword, direction, timeout, callback)
        return task.get(timeout=timeout)
        
    
@registry.client.keyword_for("zmq")
class Keyword(ClientKeyword):
    # Client keyword object for use with ZMQ.
    
    def _ktl_reads(self):
        """Is this keyword readable?"""
        return True
        
    def _ktl_writes(self):
        """Is this keyword writable?"""
        return True
        
    def _ktl_monitored(self):
        """Is this keyword monitored."""
        return self.name in self.service._monitor.monitored
        
    def _handle_response(self, message):
        """Handle a response, and return the payload."""
        self.service.log.log(5, "{0!r}.recv({1!s})".format(self, message))
        if message.iserror:
            raise DispatcherError("Dispatcher error on command: {0}".format(message.payload))
        message.verify(self.service)
        self._update(message.payload)
        return self._current_value(binary=False, both=False)
        
    def _asynchronous_command(self, command, payload, timeout=None, callback=None):
        """Execute a synchronous command."""
        return self.service._asynchronous_command(command, payload, self.name, timeout=timeout, callback=self._handle_response)
        
    def _synchronous_command(self, command, payload, timeout=None):
        """Execute a synchronous command."""
        return self.service._synchronous_command(command, payload, self.name, timeout=timeout)
        
    def wait(self, timeout=None, operator=None, value=None, sequence=None, reset=False, case=False):
        if sequence is not None:
            return sequence.wait(timeout=get_timeout(timeout))
        raise CauldronAPINotImplemented("Asynchronous expression operations are not supported for Cauldron.zmq")
    
    def monitor(self, start=True, prime=True, wait=True):
        if start:
            if prime:
                self.read(wait=wait)
            self.service._monitor.monitored.add(self.name)
        else:
            self.service._monitor.monitored.remove(self.name)
    
    def read(self, binary=False, both=False, wait=True, timeout=None):
        if not self['reads']:
            raise NotImplementedError("Keyword '{0}' does not support reads.".format(self.name))
        
        task = self._asynchronous_command("update", "", timeout=timeout)
        if wait is True:
            self.service.log.debug("{0!r}.read(wait={1}, timeout={2}) waiting.".format(self, wait, timeout))
            if not task.wait(timeout=timeout):
                raise TimeoutError("{0!r}.read(wait={1}, timeout={2}) timed out.".format(self, wait, timeout))
            return self._current_value(binary=binary, both=both)
        else:
            return task
        
    def write(self, value, wait=True, binary=False, timeout=None):
        if not self['writes']:
            raise NotImplementedError("Keyword '{0}' does not support writes.".format(self.name))
        
        # User-facing convenience to make writes smoother.
        try:
            value = self.cast(value)
        except (TypeError, ValueError):
            pass
        task = self._asynchronous_command("modify", value, timeout=timeout)
        
        if wait:
            self.service.log.debug("{0!r}.write(wait={1}, timeout={2}) waiting.".format(self, wait, timeout))
            result = task.get(timeout=timeout)
        else:
            return task
        
        