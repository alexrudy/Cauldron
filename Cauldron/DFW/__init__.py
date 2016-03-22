# -*- coding: utf-8 -*-
from __future__ import absolute_import

# Initial setup functions for this module.
# We make sure that the namespace stays very clean!
from ..api import guard_use
guard_use(msg='importing the .DFW module', error=ImportError)
del guard_use

from ..registry import dispatcher
dispatcher.setup()
del dispatcher
# Done with initial setup.

__all__ = ['Keyword', 'Service']