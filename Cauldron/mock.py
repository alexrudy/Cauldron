# -*- coding: utf-8 -*-
"""
This is a very simple mock backend for Cauldron.

It works almost identically to ``local``, but removes the requirement
that dispatchers be running before clients, and instead spawns dispatchers
to respond to any client request.
"""
from __future__ import absolute_import
from .local.dispatcher import Service as LDService
from .local.dispatcher import clear
from . import registry

__all__ = ['MDService', 'MCService']

registry.dispatcher.teardown_for("mock")(clear)

@registry.dispatcher.service_for("mock")
class Service(LDService):
    
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
    
    def __init__(self, name, populate=False):
        self._dispatcher = MDService.get_service(name)
        super(LCService, self).__init__(name, populate)
        
    def has_keyword(self, name):
        """Check for the existence of a keyword."""
        return True

MCService = Service
from .local.client import Keyword as LCKeyword
registry.client.keyword_for("mock", LCKeyword)

# Clean up the namespace.
del LDService, LDKeyword, LCKeyword