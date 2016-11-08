# -*- coding: utf-8 -*-

from __future__ import absolute_import
import functools
from . import Service
from . import Keyword

__all__ = ['write', 'read', 'wait', 'monitor', 'subscribe', 'heartbeat', 'callback']

cache = {}
def cached(service):
    """Cache service sting names."""
    try:
        svc = cache[service]
    except KeyError:
        svc = cache[service] = Service.Service(service, populate=False)
    return svc
    
def _make_cached_service_method(method):
    """Return a cached method slot-in for the procedural mode."""
    m = getattr(Service.Service, method)
    @functools.wraps(m)
    def _cached_service_method(service, *args, **kwargs):
        if not isinstance(service, str):
            raise TypeError("Service must be a string.")
        return getattr(cached(service), method)(*args, **kwargs)
    _cached_service_method.__module__ = __name__
    return _cached_service_method
    
def _make_cached_keyword_method(method):
    """Return a cached method slot-in for the procedural mode."""
    m = getattr(Keyword.Keyword, method)
    @functools.wraps(m)
    def _cached_keyword_method(service, keyword, *args, **kwargs):
        if not isinstance(service, str):
            raise TypeError("Service must be a string.")
        if not isinstance(keyword, str):
            raise TypeError("Keyword must be a string.")
        keyword = cached(service)[keyword]
        return getattr(keyword, method)(*args, **kwargs)
    _cached_keyword_method.__module__ = __name__
    return _cached_keyword_method

write = _make_cached_keyword_method('write')
read = _make_cached_keyword_method('read')
wait = _make_cached_keyword_method('wait')
monitor = _make_cached_keyword_method('monitor')
subscribe = _make_cached_keyword_method('subscribe')
callback = _make_cached_keyword_method('callback')
heartbeat = _make_cached_service_method('heartbeat')

del _make_cached_service_method, _make_cached_keyword_method
