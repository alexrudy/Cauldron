# -*- coding: utf-8 -*-
"""
The :class:`Service` will be added here by the runtime backend selection utilties.
"""

__all__ = ['Service']

cache = {}
def cached(service):
    """Cache service sting names."""
    try:
        return cache[service]
    except KeyError:
        svc = cache[service] = Service(service, populate=False)
    return svc