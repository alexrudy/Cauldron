# -*- coding: utf-8 -*-
"""
This module handles the API for the system, registering backends and using them.
"""

from __future__ import absolute_import

import six
import os
import types
import sys
import warnings
import logging
import pkg_resources

from . import registry
from .config import get_configuration
from .utils.helpers import _Setting

__all__ = ['install', 'use', 'teardown', 'use_strict_xml', 'STRICT_KTL_XML', 'APISetting']

log = logging.getLogger("Cauldron.api")

CAULDRON_SETUP = _Setting("CAULDRON_SETUP", False)
CAULDRON_ENTRYPOINT_SETUP = _Setting("CAULDRON_ENTRYPOINT_SETUP", False)

class APISetting(_Setting):
    """A setting which locks with the API use() calls."""
    def __init__(self, name, value):
        super(APISetting, self).__init__(name=name, value=value, lock=CAULDRON_SETUP)

BASENAME = ".".join(__name__.split(".")[:-1])

KTL_DEFAULT_NAMES = set(['ktl', 'DFW'])

STRICT_KTL_XML = _Setting("STRICT_KTL_XML", False)
WARN_KTL_XML = _Setting("WARN_KTL_XML", True) # Emit warnings for XML problems.
WARNINGS_KTL = _Setting("WARNINGS_KTL", False) # Emit warnings through python's warnings system.

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
        raise RuntimeError("You may only call Cauldron.use() once! It is an error to activate again.")
    
    # Entry point registration.
    setup_entry_points()
    
    if name not in registry.keys():
        eps = map(repr, pkg_resources.iter_entry_points('Cauldron.backends'))
        raise ValueError("The Cauldron backend '{0}' is not registered. Available backends are {1:s}. Entry points were {2:s}".format(
            name, ",".join(registry.keys()), ",".join(eps)))
    
    # Allow imports of backend modules now.
    CAULDRON_SETUP.on()
    
    log.info("Cauldron initialized using backend '{0}'".format(name))
    registry.client.use(name)
    registry.dispatcher.use(name)
    
    Cauldron = sys.modules[BASENAME]
    # Install the client side libraries.
    from Cauldron import ktl
    
    # Install the dispatcher side libraries.
    from Cauldron import DFW
    from Cauldron.DFW.Service import Service
    from Cauldron.DFW import Keyword
    DFW.Service = Service
    DFW.Keyword = Keyword
    
def _make_newstyle_class(base, *bases):
    """Convert a class to a new-style class."""
    return type(base.__name__, (base,) + bases + (object,), {'__module__':base.__module__})
    
@registry.client.setup_for("ktl")
def setup_ktl_backend():
    """Set up the KTL backend for ktl."""
    if "ktl" not in registry.keys():
        return
    try:
        import ktl
    except ImportError:
        pass
    else:
        from Cauldron.shim.client import Service, Keyword
        registry.client.service_for("ktl", _make_newstyle_class(ktl.Service, Service))
        registry.client.keyword_for("ktl", _make_newstyle_class(ktl.Keyword, Keyword))
        
@registry.dispatcher.setup_for("ktl")
def setup_dfw_backend():
    """Set up the KTL backend for DFW."""
    if "ktl" not in registry.keys():
        return
    try:
        import DFW
    except ImportError:
        pass
    else:
        from Cauldron.shim.dispatcher import Service, Keyword
        registry.dispatcher.service_for("ktl", _make_newstyle_class(DFW.Service, Service))
        registry.dispatcher.keyword_for("ktl", _make_newstyle_class(DFW.Keyword.Keyword, Keyword))
    
    
def check_ktl_backend():
    """Check for the KTL backend."""
    try:
        import imp
    except ImportError:
        return
    
    try:
        f, pathname, descr = imp.find_module("ktl")
    except ImportError:
        pass
    else:
        registry.client.deferred("ktl")
        if f:
            f.close()
    
    try:
        f, pathname, descr = imp.find_module("DFW")
    except ImportError:
        pass
    else:
        registry.dispatcher.deferred("ktl")
        if f:
            f.close()
    
check_ktl_backend()
    
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
    if registry.client.backend is not None:
        name = registry.client.backend
    else:
        name = "unknown"
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
        CAULDRON_SETUP.off()
        STRICT_KTL_XML.off()
        log.info("Cauldron teardown from backend '{0}'".format(name))
        
    
    
def install():
    """Install the Cauldron modules in the global namespace, so that they will intercept root-level imports.
    
    This method performs a runtime hack to try to make the Cauldron versions of ``ktl`` and ``DFW`` the ones which are
    accessed when a python module performs ``import ktl`` or ``import DFW``. If either module has already been imported
    in python, then this function will send a RuntimeWarning to that effect.
    
    .. note:: It is preferable to use :ref:`cauldron-style`, of the form ``from Cauldron import ktl``, as this will properly ensure that the Cauldron backend is invoked and not the KTL backend.
    """
    guard_use("installing Cauldron", error=RuntimeError)
    if 'ktl' in sys.modules or "DFW" in sys.modules: # pragma: no cover
        warnings.warn("'ktl' or 'DFW' already in sys.modules. Skipping 'install()'")
    sys.modules['ktl'] = sys.modules[BASENAME + ".ktl"]
    sys.modules['DFW'] = sys.modules[BASENAME + ".DFW"]

def guard_use(msg='doing this', error=RuntimeError):
    """Guard against using a Cauldron module when we haven't yet specified the backend."""
    registry.client.guard(msg, error)
    
def setup_entry_points():
    """Set up entry point registration."""
    if CAULDRON_ENTRYPOINT_SETUP:
        return
    for ep in pkg_resources.iter_entry_points('Cauldron.backends'):
        if hasattr(ep, 'resolve'):
            obj = ep.resolve()
        else:
            obj = ep.load(require=False)
        if six.callable(obj):
            obj()
    CAULDRON_ENTRYPOINT_SETUP.on()
    return
    
@registry.client.setup_for('all')
@registry.dispatcher.setup_for('all')
def setup_xml_from_config():
    """Setup XML from configuation."""
    config = get_configuration()
    if config.has_option('core', 'xmldir'):
        path = config.get("core", "xmldir")
        if path != ":notset:":
            if "RELDIR" in os.environ:
                log.warning("Overwriting environment value of RELDIR={0} to {1}".format(os.environ["RELDIR"], path))
            os.environ['RELDIR'] = path 
    if config.getboolean('core', 'strictxml'):
        STRICT_KTL_XML.on()

@registry.client.setup_for('all')
def setup_client_service_module():
    """Set up the client Service module."""
    from .ktl import Service
    Service.Service = registry.client.Service
    
def popattr(obj, name):
    """Pop an attribute during destruction."""
    try:
        delattr(obj, name)
    except AttributeError as e:
        log.debug("Failed delattr", exc_info=e)
    
@registry.client.teardown_for("all")
def teardown_client_service_module():
    """Remove the service from the client module."""
    try:
        ktls = sys.modules[BASENAME + ".ktl.Service"]
    except KeyError as e:
        pass
    else:
        popattr(ktls, 'Service')
    
    try:
        ktl = sys.modules[BASENAME + ".ktl"]
    except KeyError as e:
        pass
    else:
        popattr(ktl, 'Service')
        popattr(ktl, 'Keyword')
    
@registry.dispatcher.teardown_for("all")
def teardown_dispatcher_service_module():
    """Remove the service from the dispatcher module."""
    try:
        DFWs = sys.modules[BASENAME + ".DFW.Service"]
    except KeyError as e:
        pass
    else:
        popattr(DFWs, 'Service')
        
    
    try:
        DFW = sys.modules[BASENAME + ".DFW"]
    except KeyError as e:
        pass
    else:
        popattr(DFW, 'Service')
        popattr(DFW, 'Keyword')

@registry.dispatcher.setup_for('all')
def setup_dispatcher_service_module():
    """Set up the dispatcher Service module."""
    from .DFW import Service
    Service.Service = registry.dispatcher.Service

