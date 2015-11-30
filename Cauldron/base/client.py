# -*- coding: utf-8 -*-
"""
Implements the abstract-base Keyword and Service classes used for clients. 
This piece of Cauldron is a rough mock of :mod:`ktl`, the client side interface.

The actual implementation of client side features outside of the :class:`Keyword` and :class:`Service` classes
is in the :mod:`_ktl` module.
"""
from __future__ import absolute_import


import six
import abc
import time
import weakref
import datetime
import logging
from .core import _BaseKeyword
from ..utils.callbacks import Callbacks
from ..utils.helpers import api_not_required, api_not_implemented, api_required, api_override

__all__ = ['Keyword', 'Service']

class Keyword(_BaseKeyword):
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
    
    _ALLOWED_KEYS = ['ascii', 'binary', 'broadcasts', 'name', 'monitored', 'monitor', 'populated', 'reads', 'writes', 'timestamp', 'units']
    
    def __init__(self, service, name, type=str):
        super(Keyword, self).__init__(service, name, type)
        self._callbacks = Callbacks()
    
    @api_not_implemented
    def _ktl_broadcasts(self):
        """Does this keyword support broadcasting?"""
        pass # pragma: no cover
    
    @abc.abstractmethod
    def _ktl_monitored(self):
        """Monitored?"""
        pass # pragma: no cover
        
    def _ktl_monitor(self):
        """Delegate to monitored."""
        return self._ktl_monitored()
        
    def _ktl_populated(self):
        """Has this keyword been populated?"""
        return self._last_value is not None
        
    @abc.abstractmethod
    def _ktl_reads(self):
        """Can we read?"""
        pass # pragma: no cover
        
    @abc.abstractmethod
    def _ktl_writes(self):
        """Can we read?"""
        pass # pragma: no cover
        
    def _ktl_timestamp(self):
        """Time stamp from the last KTL read."""
        if self._last_read is not None:
            return time.mktime(self._last_read.timetuple())
        
    def _ktl_units(self):
        """KTL units."""
        return None # pragma: no cover
        
    @api_override
    def cast(self, value):
        """Cast to a native python datatype.
        
        When the "binary" value of a keyword is requested, :meth:`cast` is used to convert to the native python type.
        """
        return self._type(value)
        
    def clone(self):
        """Clone this keyword.
        """
        return self
    
    @api_not_implemented
    def isAlive(self):
        """Check that the heartbeats associated with this keyword are themselves alive; if they are, return True, otherwise return False. If no heartbeats are associated with this Keyword instance, a NoHeartbeatsError exception will be raised.
        """
        pass # pragma: no cover
        
    @api_required
    def monitor(self, start=True, prime=True, wait=True):
        """
        Subscribe to broadcasts for this KTL keyword. If start is set to False, the subscription will be shut down. If prime is set to False, there will be no priming read of the keyword value; the default behavior is to perform a priming read. If wait is set to False, the priming read (if requested) will not block while waiting for the priming read to complete.
        """
        pass # pragma: no cover
        
    @api_not_implemented
    def poll(self, period=1, start=True):
        """Poll a keyword for updates.
        
In circumstances when a KTL keyword cannot (or will not) reliably broadcast updates, polling can be established. If *start* is True, a non-blocking call to :func:`Keyword.read` will be invoked every *period* seconds; if *start* is False, polling for this keyword will be discontinued.

.. warning::
    
    Polling keywords is inefficient, as it requires a discrete ktl_read() operation for each polling event for each keyword polled. Using :func:`monitor` is a far better choice if supported by the service's KTL client library.

"""
        pass # pragma: no cover
        
    
    def callback(self, function, remove=False, preferred=False):
        """Request that a callback *function* be invoked whenever a KTL broadcast is received for this keyword.
        The callback function should accept as its sole argument a Keyword instance. If *remove* is set to False, the designated *function* will be removed from the set of active callbacks. If *preferred* is set to True, this callback will be remembered as a *preferred* callback, which gets invoked before all other non-preferred callbacks.

        :func:`callback` is typically used in conjunction with :func:`monitor`, or :func:`poll` if the specific KTL keyword does not support broadcasts.
        """
        if remove:
            return self._callbacks.discard(function)
        if preferred:
            self._callbacks.prepend(function)
        else:
            self._callbacks.add(function)
        
    
    
    def propagate(self):
        """Invoke any/all callbacks registered via :meth:`callback`. This is an internal function, invoked after a Keyword instance successfully completes a :meth:`read` call, or a KTL broadcast event occurs.
        """
        try:
            self._acting = True
            for cb in self._callbacks:
                cb(self)
        finally:
            self._acting = False
        
    @api_required
    def read(self, binary=False, both=False, wait=True, timeout=None):
        """Perform a ktl_read() operation for this keyword. The default behavior is to do a blocking read and return the ascii representation of the keyword value. If binary is set to True, only the binary representation will be returned; If both is set to True, both representations will be returned in a (binary, ascii) tuple. If wait is set to False, the KTL read operation will be performed in a background thread, and any resulting updates would trigger any callbacks registered via :meth:`callback`. If a timeout is specified (in seconds), and wait is set to True, :meth:`read` will raise a TimeoutException if the timeout expires before a response is received.
        """
        pass # pragma: no cover
        
    def subscribe(self, start=True, prime=True, wait=True):
        """Subscribe to broadcasts for this KTL keyword. If start is set to False, the subscription will be shut down. If prime is set to False, there will be no priming read of the keyword value; the default behavior is to perform a priming read. If wait is set to False, the priming read (if requested) will not block while waiting for the priming read to complete.
        """
        return self.monitor(start=start, prime=prime, wait=wait)
        
    @api_not_implemented
    def waitfor(self, expression, timeout=None, case=False):
        """Wait for a particular expression to be true.
        """
        pass # pragma: no cover
        
    @api_required
    def wait(self, timeout=None, operator=None, value=None, sequence=None, reset=False, case=False):
        """Wait for the Keyword to receive a new value, or if sequence is set, wait for the designated write operation to complete. If value is set, with or without operator being set, :meth:`wait` effectively acts as a wrapper to :meth:`waitFor`. If reset is set to True, the notification flag will be cleared before waiting against it– this is dangerous, as this introduces a race condition between the arrival of the event itself, and the invocation of :meth:`wait`. If the event occurs first, the caller may wind up waiting indefinitely. If timeout (in whole or partial seconds) is set, :meth:`wait` will return False if no update occurs before the timeout expires. Otherwise, :meth:`wait` returns True to indicate that the wait completed successfully.
        """
        pass # pragma: no cover
        
    @api_required
    def write(self, value, wait=True, binary=False, timeout=None):
        """Perform a KTL write for this keyword. value is the new value to write to the keyword. If binary is set to True, value will be interpreted as a binary representation; the default behavior is to interpret value as an ascii representation. The behavior of timeout is the same as for :meth:`read`.
        """
        pass # pragma: no cover
    
    def _update(self, value):
        """An internal callback to handle value updates."""
        self._last_read = datetime.datetime.now()
        if self._last_value != value:
            self._last_value = value
            self.propagate()
        


@six.add_metaclass(abc.ABCMeta)
class Service(object):
    """A Cauldron-based service.
    
    :param name: The KTL service name.
    :param bool populate: Whether to pre-populate this KTL service with all of the known keys.
    
    Services provide a dictionary-like access interface to KTL::
        
        >>> svc = Service('myktl')          # doctest: +SKIP
        >>> svc['mykey']                    # doctest: +SKIP
        <Keyword service=myktl name=mykey>
    
    Using dictionary indexing always returns a :class:`~Cauldron.base.keyword.Keyword` object.
    
    """
    def __init__(self, name, populate=False):
        super(Service, self).__init__()
        self._keywords = {}
        self.name = name.lower()
        self.log = logging.getLogger("ktl.Service.{0}".format(self.name))
        self._prepare()
        if populate:
            self._populate()
    
    def __del__(self):
        """Delete this service."""
        self.shutdown()
        
    def shutdown(self):
        """An explicity shutdown method."""
        pass
        
    def _prepare(self):
        """Prepare for service."""
        pass
    
    def __repr__(self):
        """Represent this object"""
        return "<Service name='{0}' at {1}>".format(self.name, hex(id(self)))
    
    def __getitem__(self, key):
        """Return a keyword."""
        if key.upper() in self._keywords:
            return self._keywords[key.upper()]
        elif self.has_keyword(key):
            return self.__missing__(key.upper())
        else:
            raise KeyError("{0} has no key '{1}'".format(self, key.upper()))
    
    def __missing__(self, key):
        """Populate and return a missing key."""
        from .._ktl.Keyword import Keyword
        keyword = Keyword(self, key)
        self._keywords[keyword.name] = keyword
        return keyword
    
    def _populate(self):
        """Populate all of the instantiated keywords here."""
        for key in self.keywords():
            self.__missing__(key)
        
        
    @api_required
    def has_keyword(self, keyword):
        """Determines if this service has a keyword.
        
        ``keyword`` can be either a Keyword instance, or a case-insensitive string.
        """
        pass # pragma: no cover
        
    def has_key(self, keyword):
        """alias for :meth:`has_keyword`"""
        return self.has_keyword(keyword)
        
    def __contains__(self, keyword):
        """alias for :meth:`has_keyword`"""
        return self.has_keyword(keyword)
    
    @api_not_implemented
    def heartbeat(self, keyword, period=5):
        """Identify keyword (either a keyword name, or a Keyword instance) as a heartbeat keyword for this Service. A heartbeat keyword should broadcast regularly to indicate that the KTL service is functional. period should be set to the maximum expected interval (in seconds) between heartbeat broadcasts.
        
        All hearbeats are monitored by a background FirstResponder thread that wakes up according to the most imminent expiration of any heartbeat’s set period. If the heartbeat does not update within period seconds, an external check will be made to see whether the service is responding. If it is, and local broadcasts have not resumed, all Service instances corresponding to the affected KTL service will be resuscitated. See the FirstResponder class and Paramedic.resuscitate() for details.
        
        Multiple heartbeats may be specified for a single Service instance. This is desirable if distinct dispatchers provide subsets of the keywords within a single KTL service. The failure of any heartbeat will trigger a full resuscitate operation; no attempt is made to distinguish between Keyword instances serviced by distinct dispatchers.
        """
        pass # pragma: no cover
        
    @api_required
    def keywords(self):
        """List all keywords available in this Service instance."""
        pass # pragma: no cover
    
    def populated(self):
        """Returns a list of all keywords (as keyword names) that are instantiated as Keyword instances within this Service instance. A Keyword instance is not created until it is deliberately requested."""
        return list(sorted(self._keywords.keys()))
        
    
    def read(self, keyword, **kwargs):
        """Read a keyword, passes through to the keyword implementation's :meth:`Keyword.read`."""
        return self[keyword].read(**kwargs)
    
    def write(self, keyword, value, **kwargs):
        """Write a keyword value, passes through to the keyword implementation's :meth:`Keyword.write`."""
        return self[keyword].write(value, **kwargs)