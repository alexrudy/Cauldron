# -*- coding: utf-8 -*-

from __future__ import absolute_import

import threading
import logging
import weakref
import contextlib
import time

from pkg_resources import parse_version

from ..utils.helpers import _Setting
from ..config import cauldron_configuration
from .. import registry

__all__ = ['REDIS_AVAILALBE', 'REDIS_DOMAIN', 'REDIS_SERVICES_REGISTRY',
    'check_redis', 'check_redis_connection',
    'redis_key_name', 'redis_status_key', 
    'REDISPubsubBase', 'REDISKeywordBase', 
    'get_connection_pool', 'set_global_connection_pool', 'get_global_connection_pool',
    'configure_pool']

REDIS_AVAILALBE = _Setting("REDIS_AVAILALBE", False)
try:
    import redis
    if parse_version(redis.__version__) >= parse_version("2.10.5"):
        REDIS_AVAILALBE.on()
except ImportError:
    REDIS_AVAILALBE.off()
finally:
    del parse_version

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
    
class PubSubWorkerThread(threading.Thread):
    def __init__(self, pubsub, sleep_time):
        super(PubSubWorkerThread, self).__init__()
        self._pubsub = pubsub
        self.sleep_time = sleep_time
        self._running = False
        self._adjust_lock = threading.RLock()
    
    @contextlib.contextmanager
    def pubsub(self):
        """Yield the pubsub object."""
        with self._adjust_lock:
            yield self._pubsub
        
    
    def run(self):
        if self._running:
            return
        self._running = True
        try:
            pubsub = self._pubsub
            lock = self._adjust_lock
            sleep_time = self.sleep_time
            while pubsub.subscribed:
                with lock:
                    pubsub.get_message(ignore_subscribe_messages=True,
                                       timeout=sleep_time)
                time.sleep(sleep_time)
        except weakref.ReferenceError as e:
            # This is a good enough reason to shutdown.
            pass
        except redis.ConnectionError as e:
            pass
        finally:
            self._running = False

    def stop(self):
        # stopping simply unsubscribes from all channels and patterns.
        # the unsubscribe responses that are generated will short circuit
        # the loop in run(), calling pubsub.close() to clean up the connection
        with self._adjust_lock:
            self._pubsub.unsubscribe()
            self._pubsub.punsubscribe()
    
class REDISPubsubBase(object):
    """A base class for handling the REDIS pubsub interface in background threads."""
    
    _thread = None
    THREAD_SLEEP_TIME = 0.001
    THREAD_DAEMON = False
    
    @contextlib.contextmanager
    def pubsub(self):
        """Get the pubsub object from the thread."""
        if self._thread is None or not self._thread.is_alive():
            yield self._pubsub
        else:
            with self._thread.pubsub() as pubsub:
                yield pubsub
    
    def _start_thread(self):
        """Create and start a new thread."""
        import redis.client
        self._thread = PubSubWorkerThread(weakref.proxy(self._pubsub), sleep_time=self.THREAD_SLEEP_TIME)
        self._thread.daemon = self.THREAD_DAEMON
        self._thread.name = "PubSubWorkerThread-{0}".format(self.name)
        self._thread.start()
    
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
    
    def shutdown(self):
        """Destructor which ensures that the child threads are stopped."""
        super(REDISPubsubBase, self).shutdown()
        if hasattr(self, "_thread"):
            self._stop_thread()
        if hasattr(self, '_pubsub'):
            try:
                self._pubsub.close()
            except KeyError as e:
                pass
    
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
                
        with self.service.pubsub() as pubsub:
            pubsub.psubscribe(**{"__keyspace@*__:"+redis_status_key(self):_message_responder})
        self.service._run_thread()
        if self.service.redis.get(redis_status_key(self)) == status:
            event.set()
        else:
            event.wait(timeout)
        with self.service.pubsub() as pubsub:
            pubsub.punsubscribe("__keyspace@*__:"+redis_status_key(self))
        return event.isSet()
        
    def _trigger_on_status(self, status, callback=None):
        """Trigger a callback on a status verb."""
        triggered = threading.Event()
        def _message_responder(message):
            if message is None:
                return # pragma: no cover
            if message['channel'].endswith(redis_status_key(self)) and message['data'] == "set":
                if self.service.redis.get(redis_status_key(self)) == status:
                    
                    with self.service.pubsub() as pubsub:
                        pubsub.unsubscribe("__keyspace@*__:"+redis_status_key(self))
                    triggered.set()
                    if callback is not None:
                        callback()
        with self.service.pubsub() as pubsub:
            pubsub.subscribe(**{"__keyspace@*__:"+redis_status_key(self):_message_responder})
        self.service._run_thread()
        # Immediately call the message responder with a fake message to ensure that the initial state is checked.
        _message_responder({'channel':redis_status_key(self), 'data':'set'})
        
    
def get_connection_pool(connection_pool):
    """Return the high-level connection pool, if it is setup."""
    if connection_pool is not None:
        return connection_pool
    else:
        return get_global_connection_pool()
    

def check_redis_connection(connection_pool=None):
    """Check a redis connection."""
    if not REDIS_AVAILALBE:
        return REDIS_AVAILALBE
    try:
        client = redis.StrictRedis(connection_pool=get_connection_pool(connection_pool))
        client.ping()
    except Exception as e:
        REDIS_AVAILALBE.off()
    return REDIS_AVAILALBE
    

_global_connection_pool = None
def get_global_connection_pool():
    """Return the global connection pool, or create it."""
    global _global_connection_pool
    if _global_connection_pool is None:
        _global_connection_pool = redis.ConnectionPool.from_url(cauldron_configuration.get("redis", "url"))
    return _global_connection_pool
    
def testing_teardown():
    """Teardown function for tests."""
    pool = get_global_connection_pool()
    r = redis.StrictRedis(connection_pool=pool)
    r.delete(r.keys("{0}:*".format(REDIS_DOMAIN)))    
    
def testing_enable_redis():
    """Enable REDIS for testing."""
    from astropy.tests.pytest_plugins import PYTEST_HEADER_MODULES
    if check_redis_connection():
        PYTEST_HEADER_MODULES['redis'] = 'redis'
        testing_teardown()
        registry.dispatcher.teardown_for("redis")(testing_teardown)
        return ["redis"]
    return []
    
@registry.dispatcher.teardown_for("redis")
@registry.client.teardown_for("redis")
def teardown():
    """Teardown the REDIS connections."""
    global _global_connection_pool
    pool = get_global_connection_pool()
    try:
        pool.disconnect()
    except:
        _global_connection_pool = None
    try:
        pool.reset()
    except:
        _global_connection_pool = None
    