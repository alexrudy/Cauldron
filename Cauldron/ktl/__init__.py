# -*- coding: utf-8 -*-
"""
This is the Cauldron implementation of :mod:`ktl`, the clinet side of the KTL keyword system. Don't import this module if you haven't called :func:`~Cauldron.api.use` to set the backend yet, this module is not importable. It is set up to match :mod:`ktl` as closely as possible.
"""
from __future__ import absolute_import

# Initial setup functions for this module.
# We make sure that the namespace stays very clean!
from ..api import guard_use
guard_use(msg='importing the .ktl module', error=ImportError)
del guard_use
# Done with initial setup.
__all__ = ['Service', 'Keyword']

# This line imports Keyword and Service.Service into the local namespace
from ..registry import client
client.setup()
del client

# From here on down we are doing things in the import order that KTL would do them.
from . import procedural