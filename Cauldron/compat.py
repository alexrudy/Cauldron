# -*- coding: utf-8 -*-
from __future__ import absolute_import

# Three-way fallback for OrderedDict
try:
    from collections import OrderedDict
except ImportError:
    # Suppress the astropy deprecation warning
    # emitted on import of this module.
    import warnings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from astropy.utils.compat.odict import OrderedDict
    except ImportError:
        from ._odict_compat import OrderedDict

import collections

try:
    from weakref import WeakSet
except ImportError:
    from .utils._weakrefset import WeakSet

__all__ = ['OrderedDict', 'WeakSet', 'WeakOrderedSet']

#TODO: Need a python2.6 implementation of WeakSet

class OrderedSet(collections.MutableSet):
    def __init__(self, values=()):
        self._od = OrderedDict().fromkeys(values)
    def __len__(self):
        return len(self._od)
    def __iter__(self):
        return iter(self._od)
    def __contains__(self, value):
        return value in self._od
    def add(self, value):
        self._od[value] = None
    def discard(self, value):
        self._od.pop(value, None)

class WeakOrderedSet(WeakSet, object):
    """An ordered implementation of WeakSet"""
    def __init__(self, values=()):
        super(WeakOrderedSet, self).__init__()
        self.data = OrderedSet()
        for elem in values: # pragma: no cover
            self.add(elem)
        