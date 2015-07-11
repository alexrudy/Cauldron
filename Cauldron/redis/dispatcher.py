# -*- coding: utf-8 -*-
"""
REDIS dispatcher.

"""
from __future__ import absolute_import

from ..base import DispatcherService, DispatcherKeyword
from ..compat import WeakOrderedSet
from .common import REDIS_SERVICES_REGISTRY, redis_key_name, get_connection_pool, check_redis
from ..api import register_dispatcher

__all__ = ['Service', 'Keyword']

class Service(DispatcherService):
    """REDIS dispatcher service."""
    
    def __init__(self, name, config, setup=None, dispatcher=None):
        redis = check_redis()
        if hasattr(dispatcher, 'connection_pool'):
            configure_pool(config)
            self.connection_pool = get_connection_pool(None)
        else:
            self.connection_pool = dispatcher.connection_pool
            
        self.redis = redis.StrictRedis(connection_pool=self.connection_pool)
        self.pubsub = redis.StrictRedis(connection_pool=self.connection_pool).pubsub()
        self._thread = None
        
        if self.redis.sismemeber(REDIS_SERVICES_REGISTRY, name.lower()):
            raise ValueError("Service {0} cannot have multiple instances.".format(name.lower()))
        
        super(Service, self).__init__(name, config, setup, dispatcher)
        self.redis.sadd(REDIS_SERVICES_REGISTRY, self.name)
        
    def _begin(self):
        """Start the pub/sub thread."""
        if self._thread is None:
            log.debug("Starting monitor thread for '{0}'".format(self.name))
            self._thread = self.pubsub.run_in_thread(sleep_time=0.001)
    
    def shutdown(self):
        """Shutdown"""
        if self._thread is not None:
            log.debug("Stopping monitor thread for '{0}'".format(self.name))
            self._thread.stop()
        self.redis.srem(REDIS_SERVICES_REGISTRY, self.name)
    

class Keyword(DispatcherKeyword):
    """A keyword"""
    
    def __init__(self, name, service, initial=None, period=None):
        """Set the initial value for this keyword."""
        super(Keyword, self).__init__(name, service, initial, period)
        self.service.pubsub.subscribe(**{redis_key_name(self):self._redis_callback})
    
    def _broadcast(self, value):
        """Broadcast that a value has changed in this keyword."""
        self.service.redis.set(redis_key_name(self), value)
    
    def _redis_callback(self, msg):
        """Take a message."""
        if msg['channel'] == self._redis_sub_name:
            try:
                self.modify(msg["data"])
            except ValueError as e:
                #TODO: respond with the error to the stream.
                pass
    

register_dispatcher(Service, Keyword)
