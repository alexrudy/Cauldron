# -*- coding: utf-8 -*-
"""
This is a very simple mock backend for Cauldron.

It works almost identically to ``local``, but removes the requirement
that dispatchers be running before clients, and instead spawns dispatchers
to respond to any client request.
"""
from __future__ import absolute_import
from .local.dispatcher import Service as LDService
from . import registry

__all__ = ['MDService', 'MCService']

@registry.dispatcher.service_for("mock")
class Service(LDService):
    """A minorly-modified service for the mock backend."""
    
    @classmethod
    def get_service(cls, name):
        """Get a service, and fallback if necessary."""
        try:
            return super(MDService, cls).get_service(name)
        except KeyError as e:
            return cls(name, config=None)
        

MDService = Service
from .local.dispatcher import Keyword as LDKeyword
registry.dispatcher.keyword_for("mock", LDKeyword)

from .local.client import Service as LCService
@registry.client.service_for("mock")
class Service(LCService):
    """Local Service"""
    def __init__(self, name, populate=False):
        try:
            self._dispatcher = MDService.get_service(name)
        except KeyError:
            raise ServiceNotStarted("Service '{0!s}' is not started.".format(name))
        super(MCService, self).__init__(name, populate)
        
    def has_keyword(self, name):
        """Check for the existence of a keyword."""
        return True

MCService = Service
from .local.client import Keyword as LCKeyword
registry.client.keyword_for("mock", LCKeyword)

# Clean up the namespace.
del LDService, LCService, LDKeyword, LCKeyword