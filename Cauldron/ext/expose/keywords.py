# -*- coding: utf-8 -*-
"""
An extension for keywords which expose pieces of native python objects.
"""
from __future__ import absolute_import

from Cauldron.types import Integer, DispatcherKeywordType
from Cauldron.exc import NoWriteNecessary

__all__ = ['ExposeAttribute']

class ExposeAttribute(DispatcherKeywordType):
    """This keyword exposes a specific attribute from an object.
    """
    
    KTL_REGISTERED = False
    
    def __init__(self, name, service, obj, attribute, *args, **kwargs):
        self._object = obj
        self._attribute = attribute
        super(HeartbeatKeyword, self).__init__(name, service, *args, **kwargs)
    
    def read(self):
        """Read this keyword from the target object."""
        return getattr(self._object, self._attribute)
    
    def write(self, value):
        """Write this keyword to the target object."""
        setattr(self._object, self._attribute, value)
    

