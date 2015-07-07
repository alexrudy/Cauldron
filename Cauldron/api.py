# -*- coding: utf-8 -*-
"""
This module handles the API for the system, registering backends and using them.
"""

from __future__ import absolute_import

import types
import sys

_client_registry = {}
_dispatcher_registry = {}

def register_client(service_class, keyword_class):
    """Register a particular client service class."""
    name = service_class.__module__.split(".")[-2]
    _client_registry[name] = (service_class, keyword_class)

try:
    from ktl import Service
except ImportError:
    pass
else:
    _client_registry['ktl'] = Service

def register_dispatcher(service_class, keyword_class):
    """docstring for register_dispatcher"""
    name = service_class.__module__.split(".")[-2]
    _dispatcher_registry[name] = (service_class, keyword_class)
    
try:
    from DFW import Service
except ImportError:
    pass
else:
    _dispatcher_registry['ktl'] = Service
    
class _KTLModule(types.ModuleType):
    """We use this funky mocked module to install in sys.modules."""
    pass

class _DFWModule(types.ModuleType):
    """We use this funky mocked module to install in sys.modules."""
    pass

basename = ".".join(__name__.split(".")[:-1])

def use(name):
    """Use a particular client name."""
    # We do some hacks here to install the module 'Cauldron.ktl' and 'Cauldron.DFW' only once this API function has been called.
    if basename + ".ktl" in sys.modules or basename + ".DFW" in sys.modules:
        raise RuntimeError("You may only call Cauldron.use() once! Refusing to activate again.")
    
    if name not in _client_registry or name not in _dispatcher_registry:
        raise ValueError("The Cauldron backend {0} is not known. Try one of {1!r}".format(
            name, list(set(_client_registry.keys() + _dispatcher_registry.keys()))
        ))
    
    _KTLModule.Service = _client_registry[name][0]
    _KTLModule.Keyword = _client_registry[name][1]
    ktl = sys.modules[basename + ".ktl"] = _KTLModule(basename + ".ktl")
    
    _DFWModule.Service = _dispatcher_registry[name][0]
    _DFWModule.Keyword = _dispatcher_registry[name][1]
    DFW = sys.modules[basename + ".DFW"] = _DFWModule(basename + ".DFW")
    
    Cauldron = sys.modules[basename]
    Cauldron.DFW = DFW
    Cauldron.ktl = ktl
    
def _teardown():
    """Teardown the Cauldron setup. This is good for test fixtures, but not much else."""
    Cauldron = sys.modules[basename]
    if hasattr(Cauldron, 'DFW'):
        del sys.modules[Cauldron.DFW.__name__]
        del Cauldron.DFW
    if hasattr(Cauldron, 'ktl'):
        del sys.modules[Cauldron.ktl.__name__]
        del Cauldron.ktl
    
    
