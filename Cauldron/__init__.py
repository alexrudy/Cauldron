# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""
Cauldron is the Abstract implementation of KTL, along with a REDIS-based concrete implementation.

Cauldron is quick-and-dirty. It doesn't implement anywhere near all of the features of KTL, and shouldn't try to.
Its just here to be a simple drop-in for KTL-based functionality.
"""

# Affiliated packages may add whatever they like to this file, but
# should keep this content at the top.
# ----------------------------------------------------------------------------
from ._astropy_init import *
# ----------------------------------------------------------------------------

def _init_log():
    """Set up some default logging options."""
    import logging
    logging.addLevelName(5, "MSG")
    if hasattr(logging, 'NullHandler'):
        logging.getLogger("DFW").addHandler(logging.NullHandler())
        logging.getLogger("ktl").addHandler(logging.NullHandler())
    del logging


# For egg_info test builds to pass, put package imports here.
if not _ASTROPY_SETUP_:
    from .api import use, install
    from . import local
    from . import redis
    from . import mock
    from . import zmq
    from . import types
    _init_log()

