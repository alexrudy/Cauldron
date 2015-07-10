# -*- coding: utf-8 -*-

import weakref
from .dispatcher import Service as Dispatcher
from ..base import ClientService, ClientKeyword
from ..exc import CauldronAPINotImplementedWarning, CauldronAPINotImplemented
from ..api import register_client

__all__ = ['Service', 'Keyword']

class Keyword(ClientKeyword):
    """A keyword for local dispatcher implementations."""
    
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
            raise NotImplementedError("Keyword '{0}' does not support reads.".format(self.name))
        
        if not wait or timeout is not None:
            warnings.warn("Cauldron.local doesn't support asynchronous reads.", CauldronAPINotImplementedWarning)
        
        self._update(self.source.update())
        return self._current_value(binary=binary, both=both)
        
    def write(self, value, wait=True, binary=False, timeout=None):
        """Write a value"""
        if not self['writes']:
            raise NotImplementedError("Keyword '{0}' does not support reads.".format(self.name))
        
        if not wait or timeout is not None:
            warnings.warn("Cauldron.local doesn't support asynchronous writes.", CauldronAPINotImplementedWarning)
            
        # User-facing convenience to make writes smoother.
        try:
            value = self.cast(value)
        except (TypeError, ValueError):
            pass
        
        #TODO: Typechecking? Error munging?
        self.source.modify(value)
        
        #TODO: Anything additional here?
        
    def wait(self, timeout=None, operator=None, value=None, sequence=None, reset=False, case=False):
        raise CauldronAPINotImplemented("Asynchronous operations are not supported for Cauldron.local")

class Service(ClientService):
    """A local service client."""
    
    def __init__(self, name, populate=False):
        self._dispatcher = Dispatcher.get(name.lower())
        super(Service, self).__init__(name, populate)
    
    def has_keyword(self, name):
        """Check for the existence of a keyword."""
        return name in self._dispatcher._keywords
        
    def keywords(self):
        """Return the list of all available keywords in this service instance."""
        return self._dispatcher.keywords()
        
    def __missing__(self, key):
        """Populate and return a missing key."""
        keyword = self._keywords[key] = Keyword(self, key)
        return keyword

register_client(Service, Keyword)
    