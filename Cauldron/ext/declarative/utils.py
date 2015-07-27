# -*- coding: utf-8 -*-
"""
Utilities for descriptor extension use.
"""
from __future__ import absolute_import

import functools

__all__ = ['descriptor__get__', 'hybridmethod']

def descriptor__get__(f):
    """A getter for descriptors."""
    @functools.wraps(f)
    def dfunc(self, obj, objtype=None):
        if obj is None:
            return self
        return f(self, obj, objtype)
    return dfunc
    
class hybridmethod(object):
    """A hybrid class and instance method"""
    def __init__(self, meth, clsmethod=None):
        super(hybridmethod, self).__init__()
        self._method = meth
        self._classmethod = clsmethod or meth
        functools.update_wrapper(self, meth)
        
    def __get__(self, instance, owner):
        """Getter to switch between hybrid and non-hybrid methods."""
        if instance is None:
            return self._classmethod.__get__(owner, owner.__class__)
        else:
            return self._method.__get__(instance, owner)
            
    
    def classmethod(self, clsmethod):
        """A decorator to set the class mehtod."""
        self._classmethod = clsmethod
        return self
        