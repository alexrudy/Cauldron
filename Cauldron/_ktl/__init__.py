# -*- coding: utf-8 -*-
"""
This is a private module that shouldn't be imported if you haven't called .use() yet. It will become the implemetnation of .ktl.

To implement new features of the KTL library here, implement them in the appropriate submodules, using relative imports in this package.
"""
from __future__ import absolute_import

# Initial setup functions for this module.
# We make sure that the namespace stays very clean!
from ..api import guard_use
guard_use(msg='importing the ._ktl module', error=ImportError)
del guard_use

from ..registry import client
client.setup()
del client
# Done with initial setup.

__all__ = ['Service', 'Keyword']