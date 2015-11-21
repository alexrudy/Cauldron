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

# For egg_info test builds to pass, put package imports here.
if not _ASTROPY_SETUP_:
    from .api import use, install
    from . import local
    from . import redis
    from . import mock
    from . import zmq
    from . import types

