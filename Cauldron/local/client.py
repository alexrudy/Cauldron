# -*- coding: utf-8 -*-

from __future__ import absolute_import

import weakref
import warnings
import threading

from .dispatcher import Service as Dispatcher
from ..base import ClientService, ClientKeyword
from ..base.core import Task as _BaseTask
from ..exc import CauldronAPINotImplementedWarning, CauldronAPINotImplemented, ServiceNotStarted, DispatcherError
from .. import registry

__all__ = ['Service', 'Keyword']


class LocalTask(_BaseTask):
    """A simple object to mock asynchronous operations."""
    pass

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
        
    def monitor(self, start=True, prime=True, wait=True):
        if prime:
            self.read(wait=wait)
        if start:
            self.source._consumers.add(self._update)
        else:
            self.source._consumers.discard(self._update)
        
    def read(self, binary=False, both=False, wait=True, timeout=None):
        """Read a value, synchronously, always."""
        
        if not self['reads']:
            raise ValueError("Keyword '{0}' does not support reads, it is write-only.".format(self.name))
        
        try:
            result = self.source.update()
        except Exception as e:
            raise DispatcherError("Error in Dispatcher: {0}".format(str(e)))
        
        task = LocalTask(result, self._update, timeout)
        task()
            
        if not wait:
            warnings.warn("Cauldron.local doesn't support asynchronous reads. Returning a fake task object.", CauldronAPINotImplementedWarning)
            return task
            
        return self._current_value(binary=binary, both=both)
        
    def write(self, value, wait=True, binary=False, timeout=None):
        """Write a value"""
        _call_msg = lambda : "{0!r}.write(wait={1}, timeout={2})".format(self, wait, timeout)
        
        if not self['writes']:
            raise ValueError("Keyword '{0}' does not support writes, it is read-only.".format(self.name))
        
        # User-facing convenience to make writes smoother.
        try:
            value = self.cast(value)
        except (TypeError, ValueError): #pragma: no cover
            pass
        
        try:
            self.source.modify(value)
            result = self.source.value
        except Exception as e:
            raise DispatcherError("Error in Dispatcher: {0}".format(str(e)))
        self.service.log.debug("{0} modified to {1}".format(_call_msg(), result))
        task = LocalTask(result, self._update, timeout)
        task()
        
        if not wait:
            warnings.warn("Cauldron.local doesn't support asynchronous writes. Returning a fake task object.", CauldronAPINotImplementedWarning)
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
    
    def has_keyword(self, name):
        """Check for the existence of a keyword."""
        return name in self._dispatcher._keywords
        
    def keywords(self):
        """Return the list of all available keywords in this service instance."""
        return self._dispatcher.keywords()
        
    def _ktl_type(self, key):
        """Return the KTL type of a named keyword."""
        return self._dispatcher[key].KTL_TYPE

    