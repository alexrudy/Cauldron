# -*- coding: utf-8 -*-
"""
REDIS dispatcher.

"""
from __future__ import absolute_import

from ..base import DispatcherService, DispatcherKeyword
from ..compat import WeakOrderedSet
from .common import REDIS_SERVICES_REGISTRY, redis_key_name, get_connection_pool, check_redis
from .. import registry

__all__ = ['Service', 'Keyword']

@registry.dispatcher.service_for("redis")
class Service(DispatcherService):
    """REDIS dispatcher service."""
    
    _thread = None
    name = None
    
    def __init__(self, name, config, setup=None, dispatcher=None):
        redis = check_redis()
        self.connection_pool = get_connection_pool(None)
        self.redis = redis.StrictRedis(connection_pool=self.connection_pool)
        self.pubsub = redis.StrictRedis(connection_pool=self.connection_pool).pubsub()
        self._thread = None
        
        if self.redis.sismember(REDIS_SERVICES_REGISTRY, name.lower()):
            raise ValueError("Service {0} cannot have multiple instances. Found {1!r}".format(name.lower(), self.redis.smembers(REDIS_SERVICES_REGISTRY)))
        
        super(Service, self).__init__(name, config, setup, dispatcher)
        
    def _begin(self):
        """Start the pub/sub thread."""
        self.redis.sadd(REDIS_SERVICES_REGISTRY, self.name)
        self._run_thread()
    
    def _run_thread(self):
        """Run the pubsub monitoring thread."""
        if self._thread is None:
            self.log.debug("Starting monitor thread for '{0}'".format(self.name))
            self._thread = self.pubsub.run_in_thread(sleep_time=0.001)
        elif not self._thread.is_alive():
            self.log.debug("Re-starting monitor thread for '{0}'".format(self.name))
            self._thread = self.pubsub.run_in_thread(sleep_time=0.001)
    
    def shutdown(self):
        """Shutdown"""
        if self._thread is not None:
            self.log.debug("Stopping monitor thread for '{0}'".format(self.name))
            self._thread.stop()
        self.redis.srem(REDIS_SERVICES_REGISTRY, self.name)
    
    def __missing__(self, key):
        """Allows the redis dispatcher to populate any keyword, whether it should exist or not."""
        return Keyword(key, self)
        

@registry.dispatcher.keyword_for("redis")
class Keyword(DispatcherKeyword):
    """A keyword"""
    
    def __init__(self, name, service, initial=None, period=None):
        """Set the initial value for this keyword."""
        super(Keyword, self).__init__(name, service, initial, period)
        self.service.pubsub.subscribe(**{redis_key_name(self):self._redis_callback})
        self.service._run_thread()
        if not self.service.redis.exists(redis_key_name(self)):
            self.service.redis.set(redis_key_name(self), '')
            self.service.redis.set(redis_key_name(self)+':status', 'init')
    
    def _broadcast(self, value):
        """Broadcast that a value has changed in this keyword."""
        self.service.redis.set(redis_key_name(self), value)
        self.service.redis.set(redis_key_name(self)+':status', 'ready')
    
    def _redis_callback(self, msg):
        """Take a message."""
        if msg['channel'] == redis_key_name(self):
            try:
                self.modify(msg["data"])
            except ValueError as e:
                #TODO: respond with the error to the stream.
                pass
                
    def set(self, value, force=False):
        """During set, lock status."""
        self.service.redis.set(redis_key_name(self)+':status', 'modify')
        try:
            super(Keyword, self).set(value, force)
        finally:
            self.service.redis.set(redis_key_name(self)+':status', 'ready')
    

