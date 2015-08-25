# -*- coding: utf-8 -*-

from __future__ import absolute_import

try:
    import redis
except ImportError:
    REDIS_AVAILALBE = False
else:
    REDIS_AVAILALBE = True

REDIS_SERVICES_REGISTRY = "{0}.SERVICES_REGISTRY".format(__name__)

def check_redis():
    """Runtime check for REDIS availability."""
    if not REDIS_AVAILALBE:
        raise RuntimeError("You must have redis.py installed to use the REDIS backend")
    return redis

def redis_key_name(service, keyword=None):
    """Return the REDIS key name for a given keyword."""
    if keyword is None:
        keyword = service
        _service = keyword.service.name
        _keyword = keyword.name
    else:
        _service, _keyword = str(service).lower(), str(keyword).upper()
    return "{0}.{1}.{2}".format(__name__, _service, _keyword)
    
def get_connection_pool(connection_pool):
    """Return the high-level connection pool, if it is setup."""
    if connection_pool is not None:
        return connection_pool
    else:
        return get_global_connection_pool()
    

_global_connection_pool = None
def get_global_connection_pool():
    """Return the global connection pool, or create it."""
    global _global_connection_pool
    if _global_connection_pool is None:
        _global_connection_pool = redis.ConnectionPool(**_connection_pool_settings)
    return _global_connection_pool
    
def set_global_connection_pool(connection_pool):
    """Set the module-level connection pool for REDIS services"""
    global _global_connection_pool
    _global_connection_pool = connection_pool

_connection_pool_settings = {}
def configure_pool(**kwargs):
    """Configure the REDIS settings from a ConfigParser object.
    
    The REDIS configuration settings must identify the host, port and database.
    
    :keyword str host: REDIS host
    :keyword int port: REDIS port
    :keyword int db: REDIS database number, usually ``0``.
    
    This function will also accept any other arguments to :class:`redis.ConnectionPool`
    
    """
    _connection_pool_settings.update(kwargs)