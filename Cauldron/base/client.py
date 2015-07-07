# -*- coding: utf-8 -*-
"""
Implements the abstract-base Keyword and Service classes used for clients.

This piece of Cauldron is a rough mock of :mod:`ktl`, the client side interface.
"""
from __future__ import absolute_import


import six
import abc
import time
import weakref
import datetime
from .core import _BaseKeyword
from ..compat import WeakOrderedSet
from ..exc import CauldronAPINotImplemented

__all__ = ['ClientKeywordBase', 'ClientServiceBase']

class ClientKeywordBase(_BaseKeyword):
    """A keyword object.
    
    Parameters
    ----------
    service : :class:`~Cauldron.base.service.Service`
        The parent KTL service.
    name : str
        The name of this keyword.
    
    Notes
    -----
    
    Each KTL keyword belongs to a specific service. The service is retained by weak reference by the keyword, to prevent reference cycles. Keyword objects only read from the keyword store when explicitly told to do so.
    
    Along with the methods of this class, the Keyword interface specifies a dictionary-like interface for accessing features of
    keywords. The dictionary interface implements the following keys:
    
    - ``ascii``: Return the keyword value in the ``ascii`` encoding.
    - ``binary``: Return a binary representation of the keyword value.
    - ``broadcasts``: Whether this keyword broadcasts changes.
    - ``name``: The name of this keyword, uppercased.
    - ``monitored``: Whether this keyword is monitored for changes.
    - ``monitor``: Same as ``monitored``.
    - ``populated``: Whether this keyword has been populated (read at least once).
    - ``reads``: Whether this keyword can be read.
    - ``writes``: Whether this keyword can be written.
    - ``timestamp``: The last modified time of this keyword, usually just the time of last read.
    - ``units``: The units of this keyword.
    
    Only one method is not supported by the original KTL library, :meth:`stop`, which could easily be subsumed into :meth:`subscribe` with the keyword argument ``start=False``.
    
    """
    
    def _ktl_broadcasts(self):
        """Does this keyword support broadcasting?"""
        raise CauldronAPINotImplemented("The cauldron API does not require support for broadcast checks.")
        
        
    @abc.abstractmethod
    def _ktl_monitored(self):
        """Monitored?"""
        pass
        
    def _ktl_monitor(self):
        """Delegate to monitored."""
        return self._ktl_monitored()
        
    def _ktl_populated(self):
        """Has this keyword been populated?"""
        return self._last_value is not None
        
    @abc.abstractmethod
    def _ktl_reads(self):
        """Can we read?"""
        pass
        
    @abc.abstractmethod
    def _ktl_writes(self):
        """Can we read?"""
        pass
        
    def _ktl_timestamp(self):
        """Time stamp from the last KTL read."""
        if self._last_read is not None:
            return time.mktime(self._last_read.timetuple())
        
    def _ktl_units(self):
        """KTL units."""
        return None
        
    def cast(self, value):
        """
        Cast to a native python datatype.
        """
        return self.type(value)
        
    def clone(self):
        """
        Clone this keyword.
        """
        return self
    
    def isAlive(self):
        """
        Check that the heartbeats associated with this keyword are themselves alive; if they are, return True, otherwise return False. If no heartbeats are associated with this Keyword instance, a NoHeartbeatsError exception will be raised.
        """
        raise CauldronAPINotImplemented("The cauldron API does not support hearbeats.")
        
    @abc.abstractmethod
    def monitor(self, start=True, prime=True, wait=True):
        """
        Subscribe to broadcasts for this KTL keyword. If start is set to False, the subscription will be shut down. If prime is set to False, there will be no priming read of the keyword value; the default behavior is to perform a priming read. If wait is set to False, the priming read (if requested) will not block while waiting for the priming read to complete.
        """
        pass
        
    def poll(self, period=1, start=True):
        """
        Poll
        """
        raise CauldronAPINotImplemented("The cauldron API does not support some background constructs.")
        
    
    def callback (self, function, remove=False, preferred=False):
        ''' Request that a callback *function* be invoked whenever
            a KTL broadcast is received for this keyword. The callback
            function should accept as its sole argument a Keyword
            instance. If *remove* is set to False, the designated
            *function* will be removed from the set of active callbacks.
            If *preferred* is set to True, this callback will be
            remembered as a *preferred* callback, which gets invoked
            before all other non-preferred callbacks.

            :func:`Keyword.callback` is typically used in conjunction
            with :func:`Keyword.monitor`, or :func:`Keyword.poll` if
            the specific KTL keyword does not support broadcasts.
        '''
        if remove:
            return self._callbacks.discard(function)
        if preferred:
            self._callbacks = WeakOrderedSet([function] + list(self._callbacks))
        else:
            self._callbacks.add(function)
    
    def propagate(self):
        """
        Invoke any/all callbacks registered via Keyword.callback(). This is an internal function, invoked after a Keyword instance successfully completes a Keyword.read() call, or a KTL broadcast event occurs.
        """
        self._acting = True
        for cb in self._callbacks:
            cb(self)
        self._acting = False
        
    @abc.abstractmethod
    def read(self, binary=False, both=False, wait=True, timeout=None):
        """
        Perform a ktl_read() operation for this keyword. The default behavior is to do a blocking read and return the ascii representation of the keyword value. If binary is set to True, only the binary representation will be returned; If both is set to True, both representations will be returned in a (binary, ascii) tuple. If wait is set to False, the KTL read operation will be performed in a background thread, and any resulting updates would trigger any callbacks registered via Keyword.callback(). If a timeout is specified (in seconds), and wait is set to True, Keyword.read() will raise a TimeoutException if the timeout expires before a response is received.
        """
        pass
        
    def subscribe(self, start=True, prime=True, wait=True):
        """
        Subscribe to broadcasts for this KTL keyword. If start is set to False, the subscription will be shut down. If prime is set to False, there will be no priming read of the keyword value; the default behavior is to perform a priming read. If wait is set to False, the priming read (if requested) will not block while waiting for the priming read to complete.
        """
        return self.monitor(start=start, prime=prime, wait=wait)
        
    def waitfor(self, expression, timeout=None, case=False):
        """Wait for a particular expression to be true."""
        raise CauldronAPINotImplemented("The Cauldron API does not support expression syntax.")
        
    @abc.abstractmethod
    def wait(self, timeout=None, operator=None, value=None, sequence=None, reset=False, case=False):
        """
        Wait for the Keyword to receive a new value, or if sequence is set, wait for the designated write operation to complete. If value is set, with or without operator being set, Keyword.wait() effectively acts as a wrapper to Keyword.waitFor(). If reset is set to True, the notification flag will be cleared before waiting against it– this is dangerous, as this introduces a race condition between the arrival of the event itself, and the invocation of Keyword.wait(). If the event occurs first, the caller may wind up waiting indefinitely. If timeout (in whole or partial seconds) is set, Keyword.wait() will return False if no update occurs before the timeout expires. Otherwise, Keyword.wait() returns True to indicate that the wait completed successfully.
        """
        
    @abc.abstractmethod
    def write(self, value, wait=True, binary=False, timeout=None):
        """
        Perform a KTL write for this keyword. value is the new value to write to the keyword. If binary is set to True, value will be interpreted as a binary representation; the default behavior is to interpret value as an ascii representation. The behavior of timeout is the same as for Keyword.read().
        """
    
    def _update(self, value):
        """An internal callback to handle value updates."""
        self._last_read = datetime.datetime.now()
        self._last_value = value
        self.propagate()
        


@six.add_metaclass(abc.ABCMeta)
class ClientServiceBase(object):
    """A Cauldron-based service.
    
    :param name: The KTL service name.
    :param bool populate: Whether to pre-populate this KTL service with all of the known keys.
    
    Services provide a dictionary-like access interface to KTL::
        
        >>> svc = Service('myktl')
        >>> svc['mykey']
        <Keyword service=myktl name=mykey>
    
    Using dictionary indexing always returns a :class:`~Cauldron.base.keyword.Keyword` object.
    
    """
    def __init__(self, name, populate=False):
        super(ClientServiceBase, self).__init__()
        self._keywords = {}
        self.name = name.lower()
        if populate:
            self._populate()
    
    def __getitem__(self, key):
        """Return a keyword."""
        if key in self._keywords:
            return self._keywords[key]
        elif self.has_keyword(key):
            self._populate_one(key)
            return self._keywords[key]
        else:
            return self.__missing__(key)
    
    def __missing__(self, key):
        """Handle a missing key."""
        raise KeyError("{0} has no key '{1}'".format(self, key))
    
    def _populate(self):
        """Populate all of the instantiated keywords here."""
        for key in self.keywords():
            self._populate_one(key)
        
        
    @abc.abstractmethod
    def has_keyword(self, keyword):
        """Determines if this service has a keyword.
        
        ``keyword`` can be either a Keyword instance, or a case-insensitive string.
        """
        pass
        
    def has_key(self, keyword):
        """alias for :meth:`has_keyword`"""
        return self.has_keyword(keyword)
        
    
    def heartbeat(self, keyword, period=5):
        """Identify keyword (either a keyword name, or a Keyword instance) as a heartbeat keyword for this Service. A heartbeat keyword should broadcast regularly to indicate that the KTL service is functional. period should be set to the maximum expected interval (in seconds) between heartbeat broadcasts.
        
        All hearbeats are monitored by a background FirstResponder thread that wakes up according to the most imminent expiration of any heartbeat’s set period. If the heartbeat does not update within period seconds, an external check will be made to see whether the service is responding. If it is, and local broadcasts have not resumed, all Service instances corresponding to the affected KTL service will be resuscitated. See the FirstResponder class and Paramedic.resuscitate() for details.
        
        Multiple heartbeats may be specified for a single Service instance. This is desirable if distinct dispatchers provide subsets of the keywords within a single KTL service. The failure of any heartbeat will trigger a full resuscitate operation; no attempt is made to distinguish between Keyword instances serviced by distinct dispatchers.
        """
        raise CauldronAPINotImplemented("The Cauldron API does not support heartbeats.")
        
    @abc.abstractmethod
    def keywords(self):
        """List all keywords available in this Service instance."""
        pass
    
    def populated(self):
        """Returns a list of all keywords (as keyword names) that are instantiated as Keyword instances within this Service instance. A Keyword instance is not created until it is deliberately requested."""
        return list(sorted(self._keywords.keys()))
        
    
    def read(self, keyword):
        """Read a keyword"""
        return self._keywords[keyword].read()
    
    def write(self, keyword, value):
        """Write a keyword value."""
        return self._keywords[keyword].write(value)