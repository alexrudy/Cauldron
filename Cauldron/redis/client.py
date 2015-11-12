# -*- coding: utf-8 -*-
"""
REDIS client tools
"""
from __future__ import absolute_import

import weakref
import time
from ..base import ClientService, ClientKeyword
from ..exc import CauldronAPINotImplementedWarning, CauldronAPINotImplemented
from .common import REDIS_SERVICES_REGISTRY, redis_key_name, check_redis, get_connection_pool, redis_status_key, REDISKeywordBase, REDISPubsubBase
from .. import registry

__all__ = ['Service', 'Keyword']

@registry.client.keyword_for("redis")
class Keyword(ClientKeyword, REDISKeywordBase):
    """A keyword for REDIS dispatcher implementations."""
    
    def _ktl_reads(self):
        """Is this keyword readable?"""
        return True
        
    def _ktl_writes(self):
        """Is this keyword writable?"""
        return True
        
    def _redis_callback(self, message):
        """A redis callback function."""
        if message is None:
            return
        if message['channel'] == redis_key_name(self) and message['data'] == "set":
            self.read()
            return
        return message
        
    def monitor(self, start=True, prime=True, wait=True):
        if prime:
            self.read(wait=wait)
        if start:
            self.service.pubsub.subscribe(**{redis_key_name(self):self._redis_callback})
            self.service._run_thread()
        else:
            self.service.pubsub.unsubscribe(redis_key_name(self))
            
    def _ktl_monitored(self):
        """Determine if this keyword is monitored."""
        return redis_key_name(self) in self.service.pubsub.channels
        
    def _update_from_redis(self):
        """Update this keyword from REDIS."""
        self._update(self.service.redis.get(redis_key_name(self)))
        
        
    def read(self, binary=False, both=False, wait=True, timeout=None):
        """Read a value, possibly asynchronously."""
        
        if not self['reads']:
            raise NotImplementedError("Keyword '{0}' does not support reads.".format(self.name))
        
        if wait or timeout is not None:
            self._wait_for_status('ready', timeout)
            self._update_from_redis()
            return self._current_value(binary=binary, both=both)
        else:
            self._trigger_on_status('ready', self._update_from_redis)
            return
        
    def write(self, value, wait=True, binary=False, timeout=None):
        """Write a value"""
        if not self['writes']:
            raise NotImplementedError("Keyword '{0}' does not support writes.".format(self.name))
        
        # User-facing convenience to make writes smoother.
        try:
            value = self.cast(value)
        except (TypeError, ValueError):
            pass
        
        self.service.redis.set(redis_key_name(self) + ":status", "modify")
        self.service.redis.publish(redis_key_name(self), value)
        if wait or timeout is not None:
            self._wait_for_status('ready', timeout)
        
    def wait(self, timeout=None, operator=None, value=None, sequence=None, reset=False, case=False):
        raise CauldronAPINotImplemented("Asynchronous operations are not supported for Cauldron.redis")

@registry.client.service_for("redis")
class Service(REDISPubsubBase, ClientService):
    """A Redis service client."""
    
    def __init__(self, name, populate=False, connection_pool=None):
        redis = check_redis()
        connection_pool = get_connection_pool(connection_pool)
        self.redis = redis.StrictRedis(connection_pool=connection_pool)
        self.pubsub = redis.StrictRedis(connection_pool=connection_pool).pubsub()
        super(Service, self).__init__(name, populate)
    
    def has_keyword(self, name):
        """Check for the existence of a keyword."""
        return self.redis.exists(redis_key_name(self.name, name))
        
    def keywords(self):
        """Return the list of all available keywords in this service instance."""
        prefix = len(redis_key_name(self.name, ""))
        return [ key[prefix:] for key in sorted(self.redis.keys(redis_key_name(self.name, "*"))) ]
        
    def __missing__(self, key):
        """Populate and return a missing key."""
        keyword = self._keywords[key] = Keyword(self, key)
        return keyword
    