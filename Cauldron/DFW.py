# -*- coding: utf-8 -*-
"""
This is a dummy module to provide the :func:`~Cauldron.api.guard_use` functionality to Cauldron.DFW

Do not place any code in this file other than the call to :func:`~Cauldron.api.guard_use` below, as it will not be used.

If you need to implement missing features in the Cauldron :mod:`DFW` module, implement them in the module :mod:`_DFW` instead. This module
will become :mod:`Cauldron.DFW` after the backend is selected via :func:`Cauldron.use`
"""
from .api import guard_use
guard_use("importing the 'DFW' module.", ImportError)