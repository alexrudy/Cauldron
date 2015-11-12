# -*- coding: utf-8 -*-

from __future__ import absolute_import

import threading
import logging
import weakref

from ..api import _Setting

try:
    import redis
except ImportError:
    REDIS_AVAILALBE = _Setting("REDIS_AVAILALBE", False)
else:
    REDIS_AVAILALBE = _Setting("REDIS_AVAILALBE", True)

REDIS_DOMAIN = "{0}".format(__name__)
REDIS_SERVICES_REGISTRY = "{0}.SERVICES_REGISTRY".format(REDIS_DOMAIN)

log = logging.getLogger(__name__)

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
    return "{0}.{1}.{2}".format(REDIS_DOMAIN, _service, _keyword)
    
def redis_status_key(service, keyword=None):
    """Return the REDIS status key name for a given keyword."""
    return "{0}:status".format(redis_key_name(service, keyword))
    
class REDISPubsubBase(object):
    """A base class for handling the REDIS pubsub interface in background threads."""
    
    _thread = None
    THREAD_SLEEP_TIME = 0.001
    
    def _start_thread(self):
        """Create and start a new thread."""
        self._thread = weakref.proxy(self.pubsub.run_in_thread(sleep_time=self.THREAD_SLEEP_TIME))
    
    def _run_thread(self):
        """Run the pubsub monitoring thread."""
        try:
            if self._thread is None:
                self.log.debug("Starting monitor thread for '{0}'".format(self.name))
                self._start_thread()
            elif not self._thread.is_alive():
                self.log.debug("Re-starting monitor thread for '{0}'".format(self.name))
                self._start_thread()
        except weakref.ReferenceError:
            self.log.debug("Re-starting monitor thread for '{0}'".format(self.name))
            self._start_thread()
        
    def _stop_thread(self):
        """Stop the underlying thread."""
        try:
            if self._thread is not None:
                self.log.debug("Stopping monitor thread for '{0}'".format(self.name))
                self._thread.stop()
        except weakref.ReferenceError:
            # Thread was already garbage collected, do nothing.
            pass
    
    def __del__(self):
        """Destructor which ensures that the child threads are stopped."""
        if hasattr(self, "_thread"):
            self._stop_thread()
    
class REDISKeywordBase(object):
    """A base class for managing REDIS Keywords"""
    
    def _wait_for_status(self, status, timeout=None, callback=None):
        """Wait for a status value to appear."""
        event = threading.Event()
        def _message_responder(message):
            if message is None:
                return # pragma: no cover
            if message['channel'].endswith(redis_status_key(self)) and message['data'] == "set":
                if status == self.service.redis.get(redis_status_key(self)):
                    event.set()
                    if callback is not None:
                        callback()
                
        self.service.pubsub.psubscribe(**{"__keyspace@*__:"+redis_status_key(self):_message_responder})
        self.service._run_thread()
        if self.service.redis.get(redis_status_key(self)) == status:
            event.set()
        else:
            event.wait(timeout)
        self.service.pubsub.punsubscribe("__keyspace@*__:"+redis_status_key(self))
        return event.isSet()
        
    def _trigger_on_status(self, status, callback=None):
        """Trigger a callback on a status verb."""
        triggered = threading.Event()
        def _message_responder(message):
            if message is None:
                return # pragma: no cover
            if message['channel'].endswith(redis_status_key(self)) and message['data'] == "set":
                if self.service.redis.get(redis_status_key(self)) == status:
                    self.service.pubsub.unsubscribe("__keyspace@*__:"+redis_status_key(self))
                    triggered.set()
                    if callback is not None:
                        callback()
        self.service.pubsub.subscribe(**{"__keyspace@*__:"+redis_status_key(self):_message_responder})
        self.service._run_thread()
        # Immediately call the message responder with a fake message to ensure that the initial state is checked.
        _message_responder({'channel':redis_status_key(self), 'data':'set'})
        
    
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