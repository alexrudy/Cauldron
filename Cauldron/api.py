# -*- coding: utf-8 -*-
"""
This module handles the API for the system, registering backends and using them.
"""

from __future__ import absolute_import

import types
import sys

__all__ = ['install', 'use', 'teardown']

CAULDRON_SETUP = False

BASENAME = ".".join(__name__.split(".")[:-1])

KTL_DEFAULT_NAMES = set(['ktl', 'DFW'])

_client_registry = {}
_client = None
_client_setup_functions = []
_dispatcher_registry = {}
_dispatcher = None
_dispatcher_setup_functions = []

# Setup Registries
def register_client_setup(func):
    """Register a client setup function."""
    _client_setup_functions.append(func)
    return func

def register_dispatcher_setup(func):
    """Register a dispathcer setup function."""
    _dispatcher_setup_functions.append(func)
    return func

def setup_dispatcher():
    """Set up the dispatcher module."""
    for func in _dispatcher_setup_functions:
        func()
    

def setup_client():
    """Set up the client module"""
    for func in _client_setup_functions:
        func()
    

# Class Registries.
def register_client(service_class, keyword_class):
    """Register a particular client service class."""
    name = service_class.__module__.split(".")[-2]
    assert name not in KTL_DEFAULT_NAMES, "Backend name '{0}' is reserved for the default KTL backend".format(name)
    _client_registry[name] = (service_class, keyword_class)

def register_dispatcher(service_class, keyword_class):
    """docstring for register_dispatcher"""
    name = service_class.__module__.split(".")[-2]
    assert name not in KTL_DEFAULT_NAMES, "Backend name '{0}' is reserved for the default KTL backend".format(name)
    _dispatcher_registry[name] = (service_class, keyword_class)

def use(name):
    """Activae a KTL backend in Cauldron.
    
    :param str name: The name of the KTL backend to use.
    
    You should only call this function once per interpreter session. It will raise a :exc:`RuntimeError` if it is called when Cauldron has been already set up. After this call, it is safe to make imports from Cauldron KTL API modules::
        
        import Cauldron
        Cauldron.use("local")
        from Cauldron import ktl
        
    
    """
    global CAULDRON_SETUP, _client, _dispatcher
    # We do some hacks here to install the module 'Cauldron.ktl' and 'Cauldron.DFW' only once this API function has been called.
    if CAULDRON_SETUP:
        raise RuntimeError("You may only call Cauldron.use() once! Refusing to activate again.")
    
    backends = set(_client_registry.keys() + _dispatcher_registry.keys()).union(KTL_DEFAULT_NAMES)
    if name not in backends:
        raise ValueError("The Cauldron backend {0} is not known. Try one of {1!r}".format(
            name, list(backends)))
    
    CAULDRON_SETUP = True
    # Set up the LROOT KTL installation differently
    if name in KTL_DEFAULT_NAMES:
        return setup_ktl_backend()
    
    # Set up the default installation, install modules.
    # Modules will call their own setup functions inside.
    _client = _client_registry[name]
    _dispatcher = _dispatcher_registry[name]
    
    Cauldron = sys.modules[BASENAME]
    # Install the client side libraries.
    from . import _ktl
    Cauldron.ktl = sys.modules[BASENAME + ".ktl"] = _ktl
    
    # Install the dispatcher side libraries.
    from . import _DFW
    Cauldron.DFW = sys.modules[BASENAME + ".DFW"] = _DFW
    
def setup_ktl_backend():
    """Set up the KTL backend."""
    Cauldron = sys.modules[BASENAME]
    import ktl
    sys.modules[BASENAME + ".ktl"] = Cauldron.ktl = ktl
    
    import DFW
    sys.modules[BASENAME + ".DFW"] = Cauldron.DFW = DFW
    
def get_client():
    """Get the client pair."""
    guard_use("accessing the client Keyword/Service pair")
    return _client
    
def get_dispatcher():
    """Get the dispatcher pair"""
    guard_use("accessing the dispatcher Keyword/Service pair")
    return _dispatcher
    
def _expunge_module(module_name):
    """Given a module name, expunge it from sys.modules."""
    mod = sys.modules[module_name]
    if mod is None:
        del sys.modules[module_name]
    else:
        try:
            if BASENAME in mod.__file__:
                del sys.modules[module_name]
        except:
            pass
    del mod
    
def teardown():
    """Remove the Cauldron setup from the sys.modules cache, and prepare for another call to :func:`use`.
    
    This method can be used to reset the state of the Cauldron module and backend. This is most appropriate in a test environemnt.
    
    .. warning:: 
        It is not guaranteed to replace modules which are currently imported and active. In fact, it suffers from many of the same problems faced
        by the builtin :func:`reload`, and to a greater extent, makes very little effort to ensure that python objects
        which have already been created and belong to the Cauldron API are handled correctly.
    """
    global CAULDRON_SETUP, _client, _dispatcher
    try:
        Cauldron = sys.modules[BASENAME]
        if hasattr(Cauldron, 'DFW'):
            for module_name in sys.modules.keys():
                if "DFW" in module_name and module_name.startswith(BASENAME):
                    _expunge_module(module_name)
            del Cauldron.DFW
        if hasattr(Cauldron, 'ktl'):
            for module_name in sys.modules.keys():
                if "ktl" in module_name and module_name.startswith(BASENAME):
                    _expunge_module(module_name)
            del Cauldron.ktl
        if "ktl" in sys.modules:
            del sys.modules['ktl']
        if "DFW" in sys.modules:
            del sys.modules["DFW"]
    except:
        raise
    finally:
        _client = None
        _dispatcher = None
        CAULDRON_SETUP = False
    
    
def install():
    """Install the Cauldron modules in the global namespace, so that they will intercept root-level imports.
    
    This method performs a runtime hack to try to make the Cauldron versions of ``ktl`` and ``DFW`` the ones which are
    accessed when a python module performs ``import ktl`` or ``import DFW``. If either module has already been imported
    in python, then this function will send a RuntimeWarning to that effect and do nothing.
    
    .. note:: It is preferable to use :ref:`cauldron-style`, of the form ``from Cauldron import ktl``, as this will properly ensure that the Cauldron backend is invoked and not the KTL backend.
    """
    guard_use("installing Cauldron", error=RuntimeError)
    if 'ktl' in sys.modules or "DFW" in sys.modules:
        warnings.warn("'ktl' or 'DFW' already in sys.modules. Skipping 'install()'")
        return
    sys.modules['ktl'] = sys.modules[BASENAME + ".ktl"]
    sys.modules['DFW'] = sys.modules[BASENAME + ".DFW"]

def guard_use(msg='doing this', error=RuntimeError):
    """Guard against using a Cauldron module when we haven't yet specified the backend."""
    if not CAULDRON_SETUP:
        raise error("You must call Cauldron.use() before {0} in order to set the Cauldron backend.".format(msg))
        
@register_client_setup
def setup_client_service_module():
    """Set up the client Service module."""
    from ._ktl import Service
    s, c = get_client()
    Service.Service = s
    
@register_dispatcher_setup
def setup_dispatcher_service_module():
    """Set up the dispathcer Service module."""
    from ._DFW import Service
    s, c = get_dispatcher()
    Service.Service = s

