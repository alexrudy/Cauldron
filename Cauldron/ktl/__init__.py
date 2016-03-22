# -*- coding: utf-8 -*-
"""
This is a private module that shouldn't be imported if you haven't called .use() yet. It will become the implemetnation of .ktl.

To implement new features of the KTL library here, implement them in the appropriate submodules, using relative imports in this package.
"""
from __future__ import absolute_import

# Initial setup functions for this module.
# We make sure that the namespace stays very clean!
from ..api import guard_use
guard_use(msg='importing the .ktl module', error=ImportError)
del guard_use
# Done with initial setup.
__all__ = ['Service', 'Keyword']

# From here on down we are doing things in the import order that KTL would do them.
from . import procedural

# This line imports Keyword and Service.Service into the local namespace
from ..registry import client
client.setup()
del client

