# -*- coding: utf-8 -*-

from __future__ import absolute_import

from . import Service

__all__ = ['write', 'read']

cache = {}
def cached(service):
    """Cache service sting names."""
    try:
        return cache[service]
    except KeyError:
        svc = cache[service] = Service.Service(service, populate=False)
    return svc

def write(service, keyword, value, *args, **kwargs):
    """Write to a keyword."""
    return cached(service)[keyword].write(value, *args, **kwargs)
    
def read(service, keyword, *args, **kwargs):
    """Read from a keyword."""
    return cached(service)[keyword].read(*args, **kwargs)
    
