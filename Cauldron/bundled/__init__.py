"""
This module is for bundled packages when we don't always want to use the bundled version.
"""
from __future__ import absolute_import

try:
    import ktlxml
except ImportError as e:
    from . import ktlxml

try:
    import GUI
except ImportError as e:
    from . import GUI
