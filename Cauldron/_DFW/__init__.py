# -*- coding: utf-8 -*-
from __future__ import absolute_import

# Initial setup functions for this module.
# We make sure that the namespace stays very clean!
from ..api import _guard_use
_guard_use(msg='importing the ._DFW module', error=ImportError)
del _guard_use

from ..api import setup_dispatcher
setup_dispatcher()
del setup_dispatcher
# Done with initial setup.

from . import Keyword
from .Service import Service
__all__ = ['Keyword', 'Service']