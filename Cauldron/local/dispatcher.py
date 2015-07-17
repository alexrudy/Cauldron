# -*- coding: utf-8 -*-
"""
Local dispatcher.

The local interface is process-local. It is lightweight, and good for testing environments, but doesn't handle anything that wouldn't normally be process local.

"""

from ..base import DispatcherService, DispatcherKeyword
from ..compat import WeakOrderedSet
from .. import registry

import weakref

__all__ = ['Service', 'Keyword']

_registry = weakref.WeakValueDictionary()

@registry.dispatcher.teardown_for("local")
def clear():
    """Clear the registry."""
    _registry.clear()

@registry.dispatcher.service_for("local")
class Service(DispatcherService):
    """Local dispatcher service."""
    
    @classmethod
    def get(cls, name):
        """Get a dispatcher for a service."""
        #TODO: Support inverse client startup ordering.
        name = str(name).lower()
        return _registry[name]
    
    def __init__(self, name, config, setup=None, dispatcher=None):
        if str(name).lower() in _registry:
            raise ValueError("Cannot have two services with name '{0}' in local registry.".format(name))
        super(Service, self).__init__(name, config, setup, dispatcher)
        
    def _begin(self):
        """Indicate that this service is ready to act, by inserting it into the local registry."""
        _registry[self.name] = self
        
    def shutdown(self):
        """To shutdown this service, delete it."""
        pass
        
    def __missing__(self, key):
        """Allows the local dispatcher to populate any keyword, whetehr it should exist or not."""
        return Keyword(key, self)

@registry.dispatcher.keyword_for("local")
class Keyword(DispatcherKeyword):
    """A keyword"""
    def __init__(self, name, service, initial=None, period=None):
        super(Keyword, self).__init__(name, service, initial, period)
        self._consumers = WeakOrderedSet()
    
    def _broadcast(self, value):
        """Notify consumers that this value has changed."""
        for consumer in self._consumers:
            consumer(value)
    
