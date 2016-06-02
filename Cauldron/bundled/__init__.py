"""
This module is for bundled packages when we don't always want to use the bundled version.
"""
from __future__ import absolute_import

try:
    import ktlxml
except ImportError as e:
    from . import ktlxml

def get_gui():
    """Function to delay import of GUI"""
    try:
        import GUI
    except ImportError as e:
        from . import GUI
    return GUI

def install_WeakRef():
    """Install the weakref module."""
    from . import WeakRef
    import sys
    sys.modules['WeakRef'] = WeakRef

install_WeakRef()
