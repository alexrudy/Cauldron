# -*- coding: utf-8 -*-

from __future__ import absolute_import

import weakref
import warnings
import logging
import threading

from six.moves import queue
from .dispatcher import Service as Dispatcher
from ..base import ClientService, ClientKeyword
from ..base.core import Task as _BaseTask
from ..exc import CauldronAPINotImplementedWarning, CauldronAPINotImplemented, ServiceNotStarted, DispatcherError, TimeoutError
from .. import registry

__all__ = ['Service', 'Keyword']


class LocalTask(_BaseTask):
    """A simple object to mock asynchronous operations."""
    
    def __call__(self):
        """Make sure that errors are properly set."""
        super(LocalTask, self).__call__()
        if self.error is not None:
            self.error = DispatcherError(str(self.error))
        if self.exc_info is not None:
            self.exc_info = (DispatcherError(str(self.error)), None, self.exc_info[2])
    
class LocalTaskQueue(threading.Thread):
    
    def __init__(self, name, log=None):
        super(LocalTaskQueue, self).__init__(name="Task Queue for {0:s}".format(name))
        self.queue = queue.Queue()
        self.log = log or logging.getLogger("ktl.local.TaskQueue.{0:s}".format(name))
        self.daemon = True
        self.shutdown = threading.Event()
    
    def run(self):
        """Run the task queue thread."""
        while not self.shutdown.isSet():
            try:
                task = self.queue.get()
                if task is None:
                    raise queue.Empty
                task()
                self.queue.task_done()
            except queue.Empty:
                pass
        
    def stop(self):
        """Stop the task-queue thread."""
        self.shutdown.set()
        try:
            self.queue.put(None, block=False)
        except queue.Full:
            pass
        else:
            self.join()

@registry.client.keyword_for("local")
class Keyword(ClientKeyword):
    
    @property
    def source(self):
        """The source of knowledge about this keyword."""
        return self.service._dispatcher[self.name]
        
    def _ktl_reads(self):
        """Is this keyword readable?"""
        return not self.source.writeonly
        
    def _ktl_writes(self):
        """Is this keyword writable?"""
        return not self.source.readonly
        
    def _ktl_monitored(self):
        """Determine if this keyword is monitored."""
        return self._update in self.source._consumers
        
    def _ktl_units(self):
        """Units for this keyword."""
        if getattr(self, '_units', None) is None:
            self._units = self.source._get_units()
        return '' if self._units is None else self._units
        
    def monitor(self, start=True, prime=True, wait=True):
        if prime:
            self.read(wait=wait)
        if start:
            self.source._consumers.add(self._update)
        else:
            self.source._consumers.discard(self._update)
        
    def _read_task(self, unused):
        result = self.source.update()
        self._update(result)
        
    def read(self, binary=False, both=False, wait=True, timeout=None):
        _call_msg = lambda : "{0!r}.read(wait={1}, timeout={2})".format(self, wait, timeout)
        
        if not self['reads']:
            raise ValueError("Keyword '{0}' does not support reads, it is write-only.".format(self.name))
        
        task = LocalTask(None, self._read_task, timeout)
        self.service._thread.queue.put(task)
        if wait:
            try:
                result = task.get(timeout=timeout)
            except TimeoutError:
                raise TimeoutError("{0} timed out.".format(_call_msg()))
            else:
                self.service.log.debug("{0} complete.".format(_call_msg()))
            return self._current_value(binary=binary, both=both)
        else:
            return task
        
    def _write_task(self, value):
        self.source.modify(value)
        self._update(self.source.value)
        return self._current_value()
        
    def write(self, value, wait=True, binary=False, timeout=None):
        _call_msg = lambda : "{0!r}.write({1}, wait={2}, timeout={3})".format(self, value, wait, timeout)
        
        if not self['writes']:
            raise ValueError("Keyword '{0}' does not support writes, it is read-only.".format(self.name))
        
        # User-facing convenience to make writes smoother.
        try:
            value = self.cast(value)
        except (TypeError, ValueError): #pragma: no cover
            pass
        
        task = LocalTask(value, self._write_task, timeout)
        self.service._thread.queue.put(task)
        if wait:
            self.service.log.debug("{0} waiting.".format(_call_msg()))
            try:
                result = task.get(timeout=timeout)
            except TimeoutError:
                raise TimeoutError("{0} timed out.".format(_call_msg()))
            else:
                self.service.log.debug("{0} complete.".format(_call_msg()))
            self.service.log.debug("{0} complete.".format(_call_msg()))
            return
        else:
            return task
        
    def wait(self, timeout=None, operator=None, value=None, sequence=None, reset=False, case=False):
        if sequence is not None:
            return sequence.wait()
        raise CauldronAPINotImplemented("Asynchronous operations are not supported for Cauldron.local")

@registry.client.service_for("local")
class Service(ClientService):
    
    def __init__(self, name, populate=False):
        try:
            self._dispatcher = Dispatcher.get_service(name)
        except KeyError:
            raise ServiceNotStarted("Service '{0!s}' is not started.".format(name))
        super(Service, self).__init__(name, populate)
        
    def _prepare(self):
        """Prepare the local client for action."""
        self._thread = LocalTaskQueue(self.name, self.log)
        self._thread.start()
    
    def shutdown(self):
        """Shutdown this client."""
        if hasattr(self, '_thread'):
            self._thread.stop()
        super(Service, self).shutdown()
    
    def _has_keyword(self, name):
        """Check for the existence of a keyword."""
        return name in self._dispatcher._keywords
        
    def keywords(self):
        """Return the list of all available keywords in this service instance."""
        return self._dispatcher.keywords()
        
    def _ktl_type(self, key):
        """Return the KTL type of a named keyword."""
        return self._dispatcher[key].KTL_TYPE

    