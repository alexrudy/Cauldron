# -*- coding: utf-8 -*-
"""
REDIS dispatcher.

"""
from __future__ import absolute_import

import weakref

from ..base import DispatcherService, DispatcherKeyword
from ..compat import WeakOrderedSet
from .common import REDIS_SERVICES_REGISTRY, redis_key_name, get_connection_pool, check_redis, REDISPubsubBase, teardown
from .. import registry

__all__ = ['Service', 'Keyword']

registry.dispatcher.teardown_for("redis")(teardown)

@registry.dispatcher.service_for("redis")
class Service(REDISPubsubBase, DispatcherService):
    """REDIS dispatcher service."""
    
    name = None
    THREAD_DAEMON = True
    
    def __init__(self, name, config, setup=None, dispatcher=None):
        redis = check_redis()
        self.connection_pool = get_connection_pool(None)
        self.redis = redis.StrictRedis(connection_pool=self.connection_pool)
        self.redis.config_set("notify-keyspace-events", "KA")
        self._pubsub = redis.StrictRedis(connection_pool=self.connection_pool).pubsub()
        
        if self.redis.sismember(REDIS_SERVICES_REGISTRY, name.lower()):
            raise ValueError("Service {0} cannot have multiple instances. Found {1!r}".format(name.lower(), self.redis.smembers(REDIS_SERVICES_REGISTRY)))
        
        super(Service, self).__init__(name, config, setup, dispatcher)
        
    def _begin(self):
        """Start the pub/sub thread."""
        self.redis.sadd(REDIS_SERVICES_REGISTRY, self.name)
        self._run_thread()
    
    def shutdown(self):
        """Shutdown"""
        self._stop_thread()
        self.redis.srem(REDIS_SERVICES_REGISTRY, self.name)
    
    def __del__(self):
        """Destructor!"""
        super(Service, self).__del__()
        if hasattr(self, "redis"):
            self.redis.srem(REDIS_SERVICES_REGISTRY, self.name)
        

@registry.dispatcher.keyword_for("redis")
class Keyword(DispatcherKeyword):
    """A keyword"""
    
    def __init__(self, name, service, initial=None, period=None):
        """Set the initial value for this keyword."""
        super(Keyword, self).__init__(name, service, initial, period)
        with self.service.pubsub() as pubsub:
            pubsub.subscribe(**{redis_key_name(self):self._redis_callback})
        self.service._run_thread()
        if not self.service.redis.exists(redis_key_name(self)):
            self.service.redis.set(redis_key_name(self), '')
            self.service.redis.set(redis_key_name(self)+':status', 'init')
            self.service.redis.set(redis_key_name(self)+':type', self.KTL_TYPE)
    
    def _redis_set_status(self, status):
        """Set REDIS status for a keyword."""
        self.service.log.log(5, "Setting '{0}' status = '{1}' from '{2}'".format(self.name, status, 
            self.service.redis.get(redis_key_name(self)+':status')))
        self.service.redis.set(redis_key_name(self)+':status', status)
        if status != "error":
            if self.service.redis.exists(redis_key_name(self)+':error'):
                self.service.log.log(5, "Clearing error for '{0}'".format(self.name))
                self.service.redis.delete(redis_key_name(self)+':error')
    
    def _broadcast(self, value):
        """Broadcast that a value has changed in this keyword."""
        self.service.redis.set(redis_key_name(self), value)
    
    def _redis_callback(self, msg):
        """Take a message."""
        if msg['channel'] == redis_key_name(self):
            try:
                self.service.log.log(5, "'{0}' modify({1})".format(self.name, msg["data"]))
                self.modify(msg["data"])
            except Exception as e:
                self.service.log.error("Error in the REDIS responder thread for set({0!s}): {1!s}".format(msg["data"], e))
                self.service.redis.set(redis_key_name(self)+':error', str(e))
                self.service.redis.set(redis_key_name(self)+':status', 'error')
            
    def set(self, value, force=False):
        """During set, lock status."""
        self.service.redis.set(redis_key_name(self)+':status', 'modify')
        try:
            super(Keyword, self).set(value, force)
        except Exception as e:
            self.service.redis.set(redis_key_name(self)+':error', str(e))
            self._redis_set_status('error')
            raise
        else:
            self.service.redis.set(redis_key_name(self)+':status', 'ready')
    

