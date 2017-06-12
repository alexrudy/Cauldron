# -*- coding: utf-8 -*-
"""
ZMQ Client Implementation
"""

from __future__ import absolute_import

import weakref
from ..base import ClientService, ClientKeyword
from ..exc import CauldronAPINotImplementedWarning, CauldronAPINotImplemented, DispatcherError, TimeoutError
from .common import zmq_get_address, check_zmq, teardown, zmq_connect_socket
from .thread import ZMQThread
from .protocol import ZMQCauldronMessage, ZMQCauldronErrorResponse, FRAMEBLANK, PrefixMatchError, FrameFailureError
from .tasker import Task, TaskQueue
from .broker import ZMQBroker
from .responder import ZMQDispatcherError
from .. import registry
from ..config import get_configuration, get_timeout
from ..logger import KeywordMessageFilter
from ..compat import WeakSet

import atexit
import json
import six
import threading
import logging
import warnings

__all__ = ["Service", "Keyword"]

def teardown():
    """Teardown registered instances."""
    _cleanup()

registry.client.teardown_for('zmq')(teardown)

_service_registry = WeakSet()

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


class _ZMQMonitorThread(ZMQThread):
    """A monitoring thread for ZMQ-powered Services which listens for broadcasts."""
    def __init__(self, service):
        super(_ZMQMonitorThread, self).__init__(name="ktl.Service.{0}.Broadcasts".format(service.name), context=service.ctx)
        self.service = weakref.proxy(service)
        self.monitored = set()
        self.address = None
        self.daemon = True
        
    def thread_target(self):
        """Run the monitoring thread."""
        zmq = check_zmq()
        try:
            ctx = self.service.ctx
        except weakref.ReferenceError:
            self.log.debug("Can't start ZMQ monitor, service has disappeared.")
            return
        
        socket = ctx.socket(zmq.SUB)
        signal = self.get_signal_socket()
        poller = zmq.Poller()
        poller.register(signal, zmq.POLLIN)
        poller.register(socket, zmq.POLLIN)
        
        try:
            zmq_connect_socket(socket, get_configuration(), "subscribe", log=self.log, label='client-monitor', address=self.address)
            # Accept everything belonging to this service.
            socket.setsockopt_string(zmq.SUBSCRIBE, six.text_type(self.service.name))
            
            self.started.set()
            while self.running.is_set():
                ready = dict(poller.poll(timeout=1e3))
                if signal in ready:
                    _ = signal.recv()
                    self.log.trace("Got a signal: .running = {0}".format(self.running.is_set()))
                    continue
                if socket in ready:
                    try:
                        message = ZMQCauldronMessage.parse(socket.recv_multipart())
                        message.verify(self.service)
                        keyword = self.service[message.keyword]
                        f = KeywordMessageFilter(keyword)
                        self.log.addFilter(f)
                        try:
                            if keyword.name in self.monitored:
                                keyword._update(message.unwrap())
                                self.log.trace("{0!r}.monitor({1}={2})".format(self, keyword.name, message.unwrap()))
                            else:
                                self.log.trace("{0!r}.monitor({1}) ignored".format(self, keyword.name))
                        except Exception as e:
                            self.log.exception("{0!r}._update() error: {1!r}".format(keyword, e))
                        finally:
                            self.log.removeFilter(f)
                    except PrefixMatchError as e:
                        self.log.trace("{0!r}.monitor() ignored".format(self))
                    except ZMQCauldronErrorResponse as e:
                        self.log.error("Broadcast Message Error: {0!r}".format(e))
                    except (zmq.ContextTerminated, zmq.ZMQError):
                        raise
                    except Exception as e:
                        self.log.exception("Broadcast error: {0!r}".format(e))
        except (zmq.ContextTerminated, zmq.ZMQError) as e:
            self.log.trace("Service shutdown and context terminated, closing broadcast thread. {0}".format(repr(e)))
        else:
            try:
                socket.close(linger=0)
            except:
                pass
        finally:
            signal.close(linger=0)
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
        _service_registry.add(self)
        super(Service, self).__init__(name, populate)
        
    def _prepare(self):
        """Prepare step."""
        if not ZMQBroker.check(ctx=self.ctx):
            raise ZMQDispatcherError("Can't locate a suitable dispatcher for {0}".format(self.name))
        self._monitor = _ZMQMonitorThread(self)
        self._tasker = TaskQueue("ktl.Service.{0:s}.Tasks".format(self.name), ctx=self.ctx, log=self.log)
        self._tasker.daemon = True
        self._tasker.start()
        address = self._synchronous_command("lookup", "subscribe", direction="CBQ")
        self._monitor.address = address
        self._monitor.start()
        
    def _ktl_type(self, key):
        """Get the KTL type of a specific keyword."""
        name = key.upper()
        with self._lock:
            try:
                ktl_type = self._type_ktl_cache[name]
            except KeyError:
                ktl_type = self._lookup_ktl_type(name)
        return ktl_type
        
    def _lookup_ktl_type(self, name):
        """Lookup the KTL type for a key."""
        try:
            message = self._synchronous_command("identify", payload=name, keyword=name, direction="CSQ")
        except FrameFailureError:
            raise KeyError("Keyword '{0}' does not exist.".format(name))
        else:
            items = list(set(message.split(":")))
            if len(items) == 1:
                ktl_type = items[0]
            else:
                raise KeyError("Keyword '{0}' is multiply defined.".format(name))
        self._type_ktl_cache[name] = ktl_type
        return ktl_type
        
    def __del__(self):
        """On delete, try to shutdown."""
        self.shutdown()
        
    def shutdown(self):
        if hasattr(self, '_monitor') and self._monitor is not None and self._monitor.isAlive():
            self.log.trace("Stopping monitor")
            self._monitor.stop()
            self.log.trace("Stopped monitor")
        if hasattr(self, '_tasker') and self._tasker is not None and self._tasker.isAlive():
            self.log.trace("Stopping tasker")
            self._tasker.stop()
            self.log.trace("Stopped tasker")
        
    def _has_keyword(self, name):
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
        self.log.msg("{0!r}.recv({1!s})".format(self, message))
        if message.iserror:
            raise DispatcherError("Dispatcher error on command: {0}".format(message.payload))
        message.verify(self)
        return message.unwrap()
    
    def _asynchronous_command(self, command, payload, keyword=None, direction="CDQ", timeout=None, callback=None):
        """Run an asynchronous command."""
        callback = callback or self._handle_response
        return self._tasker.asynchronous_command(command, payload, self, keyword, direction, timeout, callback)
        
    def _synchronous_command(self, command, payload, keyword=None, direction="CDQ", timeout=None, callback=None):
        """Execute a synchronous command."""
        callback = callback or self._handle_response
        return self._tasker.synchronous_command(command, payload, self, keyword, direction, timeout, callback)
        
    
@registry.client.keyword_for("zmq")
class Keyword(ClientKeyword):
    # Client keyword object for use with ZMQ.
    
    def _prepare(self):
        """Prepare this keyword for use."""
        if self.KTL_TYPE == 'enumerated':
            self._async_units()
    
    def _ktl_reads(self):
        """Is this keyword readable?"""
        return True
        
    def _ktl_writes(self):
        """Is this keyword writable?"""
        return True
        
    def _ktl_monitored(self):
        """Is this keyword monitored."""
        return self.name in self.service._monitor.monitored
        
    def _ktl_units(self):
        """Get KTL units."""
        if getattr(self, '_units', None) is None:
            timeout = get_timeout(None)
            if not hasattr(self, '_got_units'):
                self._async_units(timeout)
            self._got_units.wait(timeout)
            if not self._got_units.is_set():
                raise DispatcherError("Dispatcher error on command 'units'.")
        return '' if self._units is None else self._units
        
    def _async_units(self, timeout=None):
        """Asynchronously request units."""
        self._got_units = threading.Event()
        return self._asynchronous_command("units", "", timeout=timeout, callback=self._handle_units)
        
    def _handle_units(self, message):
        """Handle a message response which has units.."""
        self.log.msg("{0!r}.recv({1!s})".format(self, message))
        if message.iserror:
            raise DispatcherError("Dispatcher error on command: {0}".format(message.payload))
        message.verify(self.service)
        self._units = json.loads(message.unwrap())
        self._got_units.set()
        return self._units
    
    def _handle_response(self, message):
        """Handle a response, and return the payload."""
        self.log.msg("{0!r}.recv({1!s})".format(self, message))
        if message.iserror:
            self.log.error("Dispatcher error: {0}".format(message))
            raise DispatcherError("Dispatcher error on command: {0}".format(message.payload))
        message.verify(self.service)
        self._update(message.unwrap())
        return self._current_value(binary=False, both=False)
        
    def _asynchronous_command(self, command, payload, timeout=None, callback=None):
        """Execute a synchronous command."""
        return self.service._asynchronous_command(command, payload, self.name, timeout=timeout, callback=callback or self._handle_response)
        
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
    
    def _await(self, task, timeout, _call_msg=None):
        """Await an asynchronous task."""
        if _call_msg is None:
            _call_msg = lambda : "{0!r}_await(task={1!r}, timeout={2!r})".format(self, task, timeout)
        
        self.service.log.trace("{0} waiting.".format(_call_msg()))
        try:
            result = task.get(timeout=timeout)
        except TimeoutError:
            raise TimeoutError("{0} timed out.".format(_call_msg()))
        else:
            self.service.log.trace("{0} complete.".format(_call_msg()))
        return result
    
    def read(self, binary=False, both=False, wait=True, timeout=None):
        _call_msg = lambda : "{0!r}.read(wait={1}, timeout={2})".format(self, wait, timeout)
        
        if not self['reads']:
            raise NotImplementedError("Keyword '{0}' does not support reads.".format(self.name))
        
        task = self._asynchronous_command("update", "", timeout=timeout)
        if wait:
            self._await(task, timeout, _call_msg)
            return self._current_value(binary=binary, both=both) 
        else:
            return task
        
    def write(self, value, wait=True, binary=False, timeout=None):
        _call_msg = lambda : "{0!r}.write(wait={1}, timeout={2})".format(self, wait, timeout)
        
        if not self['writes']:
            raise NotImplementedError("Keyword '{0}' does not support writes.".format(self.name))
        
        # User-facing convenience to make writes smoother.
        try:
            value = self.cast(value)
        except (TypeError, ValueError):
            pass
        self.service.log.trace("{0} = {1}".format(_call_msg(), value))
        task = self._asynchronous_command("modify", value, timeout=timeout)
        if wait:
            return self._await(task, timeout, _call_msg)
        else:
            return task
        
        