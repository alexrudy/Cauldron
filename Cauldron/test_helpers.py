# -*- coding: utf-8 -*-
"""
This module contains code which is useful when twesting against a Cauldron-based application.

It is also used internally in Cauldron to facilitate testing of the module itself.
"""

import sys
import pkg_resources
from .utils._weakrefset import WeakSet

def setup_entry_points_api():
    """Set up the entry points API if Cauldron isn't installed."""
    from . import registry
    if any(backend not in registry.keys() for backend in ["zmq", "local"]):
        from .zmq import setup_zmq_backend
        setup_zmq_backend()
        from .local import setup_local_backend
        setup_local_backend()
        from . import mock

def get_available_backends():
    """Return the set of available backends from Cauldron."""
    from . import registry
    setup_entry_points_api()
    available_backends = set(registry.keys())
    available_backends.discard("mock")
    return available_backends
    
SEEN_THREADS = WeakSet()
def fail_if_not_teardown():
    """Fail a pytest teardown if Cauldron has not ended properly.
    
    First, calls :func:`~Cauldron.api.teardown`. Then checks that modules can't be imported any more.
    Next, checks that all threads that are supposed to die, actually die.
    """
    from Cauldron.api import teardown, CAULDRON_SETUP
    teardown()
    
    # Check modules not in sys.modules
    failures = ["DFW", "ktl", "_DFW", "_ktl"]
    if CAULDRON_SETUP:
        raise ValueError("Cauldron is marked as 'setup'.")
    for module in sys.modules:
        for failure in failures:
            if failure in module.split("."):
                mod = sys.modules[module]
                if mod is not None:
                    raise ValueError("Module {0}/{1} not properly torn down.".format(module, sys.modules[module]))
    
    # Check for importability
    try:
        from Cauldron import DFW
    except ImportError as e:
        pass
    else:
        raise ValueError("Shouldn't be able to import DFW now!")
    
    try:
        from Cauldron import ktl
    except ImportError as e:
        pass
    else:
        raise ValueError("Shouldn't be able to import ktl now!")
    
    # Check for zombie threads.
    import threading, time
    if threading.active_count() > 1:
        time.sleep(0.1) #Allow zombies to die!
    count = 0
    for thread in threading.enumerate():
        if not thread.daemon and thread not in SEEN_THREADS:
            count += 1
            SEEN_THREADS.add(thread)
            
    # If there are new, non-daemon threads, cause an error.
    if count > 1:
        threads_str = "\n".join([repr(thread) for thread in threading.enumerate()])
        raise ValueError("{0:d} non-deamon thread{1:s} left alive!\n{2!s}".format(
            count-1, "s" if (count-1)>1 else "", threads_str))