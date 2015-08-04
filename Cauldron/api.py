# -*- coding: utf-8 -*-
"""
This module handles the API for the system, registering backends and using them.
"""

from __future__ import absolute_import

import types
import sys
import logging
import warnings

logging.basicConfig(level=logging.DEBUG)

from . import registry

__all__ = ['install', 'use', 'teardown', 'use_strict_xml', 'STRICT_KTL_XML']

class _Setting(object):
    """A settings object, which can be passed around by value."""
    def __init__(self, name, value):
        super(_Setting, self).__init__()
        self.name = name
        self.value = value
    
    def __repr__(self):
        """Represent this value"""
        return "<Setting {0}={1}>".format(self.name, self.value)
    
    def __nonzero__(self):
        """Cast this setting to it's own boolean value."""
        return bool(self.value)
        
    def on(self):
        """Turn this setting on."""
        self.value = True
    
    def off(self):
        """Turn this setting off."""
        self.value = False

CAULDRON_SETUP = _Setting("CAULDRON_SETUP", False)

BASENAME = ".".join(__name__.split(".")[:-1])

KTL_DEFAULT_NAMES = set(['ktl', 'DFW'])

STRICT_KTL_XML = _Setting("STRICT_KTL_XML", False)

def use_strict_xml():
    """Use strict XML settings. Strict XML enforces all of the KTL XML rules to the letter, and requires that all keywords be pre-defined in XML files which are loaded when connecting a service from either the client or dispatcher side.
    
    If strict XML is not used, Cauldron will provide warnings when XML rules are violated, but will continue to operate."""
    STRICT_KTL_XML.on()

def use(name):
    """Activae a KTL backend in Cauldron.
    
    :param str name: The name of the KTL backend to use.
    
    You should only call this function once per interpreter session. It will raise a :exc:`RuntimeError` if it is called when Cauldron has been already set up. After this call, it is safe to make imports from Cauldron KTL API modules::
        
        import Cauldron
        Cauldron.use("local")
        from Cauldron import ktl
        
    
    """
    # We do some hacks here to install the module 'Cauldron.ktl' and 'Cauldron.DFW' only once this API function has been called.
    if CAULDRON_SETUP:
        raise RuntimeError("You may only call Cauldron.use() once! Refusing to activate again.")
    
    if name not in registry.keys():
        raise ValueError("The Cauldron backend {0} is not known. Try one of {1!r}".format(
            name, list(registry.keys())))
    
    # Allow imports of backend modules now.
    CAULDRON_SETUP.on()
    
    # Set up the LROOT KTL installation differently
    if name in KTL_DEFAULT_NAMES: # pragma: no cover
        return setup_ktl_backend()
    
    registry.client.use(name)
    registry.dispatcher.use(name)
    
    Cauldron = sys.modules[BASENAME]
    # Install the client side libraries.
    from . import _ktl
    from ._ktl.Service import Service
    from ._ktl import Keyword
    _ktl.Service = Service
    _ktl.Keyword = Keyword
    Cauldron.ktl = sys.modules[BASENAME + ".ktl"] = _ktl
    
    # Install the dispatcher side libraries.
    from . import _DFW
    from ._DFW.Service import Service
    from ._DFW import Keyword
    _DFW.Service = Service
    _DFW.Keyword = Keyword
    Cauldron.DFW = sys.modules[BASENAME + ".DFW"] = _DFW
    
def setup_ktl_backend(): # pragma: no cover
    """Set up the KTL backend."""
    Cauldron = sys.modules[BASENAME]
    import ktl
    sys.modules[BASENAME + ".ktl"] = Cauldron.ktl = ktl
    
    import DFW
    sys.modules[BASENAME + ".DFW"] = Cauldron.DFW = DFW
    
def _expunge_module(module_name):
    """Given a module name, expunge it from sys.modules."""
    mod = sys.modules[module_name]
    if mod is None:
        del sys.modules[module_name]
    else:
        try:
            del sys.modules[module_name]
        except: # pragma: no cover
            pass
    del mod
    
def _is_target_module(name, module_name):
    """Check a module name."""
    return (name in module_name.split(".") or "_{0}".format(name) in module_name.split(".")) and module_name.startswith(BASENAME)
    
def teardown():
    """Remove the Cauldron setup from the sys.modules cache, and prepare for another call to :func:`use`.
    
    This method can be used to reset the state of the Cauldron module and backend. This is most appropriate in a test environemnt.
    
    .. warning:: 
        It is not guaranteed to replace modules which are currently imported and active. In fact, it suffers from many 
        of the same problems faced by the builtin :func:`reload`, and to a greater extent, makes very little effort to 
        ensure that python objects which have already been created and belong to the Cauldron API are handled correctly. 
        It is likely that if you call this method with instances of Keyword or Service still active in your application,
        those instances will become unusable.
    """
    registry.teardown()
    try:
        Cauldron = sys.modules[BASENAME]
        if hasattr(Cauldron, 'DFW'):
            del Cauldron.DFW
        for module_name in sys.modules.keys():
            if _is_target_module("DFW", module_name):
                _expunge_module(module_name)
        if hasattr(Cauldron, 'ktl'):
            del Cauldron.ktl
        for module_name in sys.modules.keys():
            if _is_target_module("ktl", module_name):
                _expunge_module(module_name)
        if "ktl" in sys.modules:
            del sys.modules['ktl']
        if "DFW" in sys.modules:
            del sys.modules["DFW"]
    except: # pragma: no cover
        raise
    finally:
        STRICT_KTL_XML.off()
        CAULDRON_SETUP.off()
    
    
def install():
    """Install the Cauldron modules in the global namespace, so that they will intercept root-level imports.
    
    This method performs a runtime hack to try to make the Cauldron versions of ``ktl`` and ``DFW`` the ones which are
    accessed when a python module performs ``import ktl`` or ``import DFW``. If either module has already been imported
    in python, then this function will send a RuntimeWarning to that effect and do nothing.
    
    .. note:: It is preferable to use :ref:`cauldron-style`, of the form ``from Cauldron import ktl``, as this will properly ensure that the Cauldron backend is invoked and not the KTL backend.
    """
    guard_use("installing Cauldron", error=RuntimeError)
    if 'ktl' in sys.modules or "DFW" in sys.modules: # pragma: no cover
        warnings.warn("'ktl' or 'DFW' already in sys.modules. Skipping 'install()'")
        return
    sys.modules['ktl'] = sys.modules[BASENAME + ".ktl"]
    sys.modules['DFW'] = sys.modules[BASENAME + ".DFW"]

def guard_use(msg='doing this', error=RuntimeError):
    """Guard against using a Cauldron module when we haven't yet specified the backend."""
    if not CAULDRON_SETUP:
        raise error("You must call Cauldron.use() before {0} in order to set the Cauldron backend.".format(msg))
        
@registry.client.setup_for('all')
def setup_client_service_module():
    """Set up the client Service module."""
    from ._ktl import Service
    Service.Service = registry.client.Service
    
@registry.client.teardown_for("all")
def teardown_client_service_module():
    """Remove the service from the client module."""
    try:
        _ktls = sys.modules[BASENAME + "._ktl.Service"]
        del _ktls.Service
        _ktl = sys.modules[BASENAME + "._ktl"]
        del _ktl.Service
        del _ktl.Keyword
    except KeyError as e:
        pass
    
    
@registry.dispatcher.teardown_for("all")
def teardown_dispatcher_service_module():
    """Remove the service from the dispatcher module."""
    try:
        _DFWs = sys.modules[BASENAME + "._DFW.Service"]
        del _DFWs.Service
        _DFW = sys.modules[BASENAME + "._DFW"]
        del _DFW.Service
        del _DFW.Keyword
    except KeyError as e:
        pass
    

@registry.dispatcher.setup_for('all')
def setup_dispatcher_service_module():
    """Set up the dispatcher Service module."""
    from ._DFW import Service
    Service.Service = registry.dispatcher.Service

