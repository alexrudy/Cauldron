# -*- coding: utf-8 -*-
"""
This is a private module that shouldn't be imported if you haven't called .use() yet. It will become the implemetnation of .ktl.

To implement new features of the KTL library here, implement them in the appropriate submodules, using relative imports in this package.
"""
from __future__ import absolute_import

# Initial setup functions for this module.
# We make sure that the namespace stays very clean!
from ..api import _guard_use
_guard_use(msg='importing the ._ktl module', error=ImportError)
del _guard_use

from ..api import setup_client
setup_client()
del setup_client
# Done with initial setup.

from .Keyword import Keyword
from .Service import Service

__all__ = ['Service', 'Keyword']