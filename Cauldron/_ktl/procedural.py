# -*- coding: utf-8 -*-

from __future__ import absolute_import

from . import Service

__all__ = ['write', 'read']

def write(service, keyword, value, *args, **kwargs):
    """Write to a keyword."""
    return Service.cached(service)[keyword].write(value, *args, **kwargs)
    
def read(service, keyword, *args, **kwargs):
    """Read from a keyword."""
    return Service.cached(service)[keyword].read(*args, **kwargs)
    
