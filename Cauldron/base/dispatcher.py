# -*- coding: utf-8 -*-
"""
Implements the abstract-base Keyword and Service classes used for dispatchers. 
This piece of Cauldron is a rough mock of :mod:`DFW`, the dispatcher side interface.
"""

from __future__ import absolute_import

import abc
import six
import weakref
from ..compat import WeakOrderedSet
from .core import _BaseKeyword
from ..exc import CauldronAPINotImplemented, NoWriteNecessary
from ..utils.helpers import api_not_required, api_not_implemented, api_required, api_override

__all__ = ['DispatcherKeyword', 'DispatcherService']

class DispatcherKeyword(_BaseKeyword):
    """A dispatcher-based keyword, which should own its own values."""
    
    _ALLOWED_KEYS = set(['value', 'name', 'readonly', 'writeonly'])
    
    def __init__(self, name, service, initial=None, period=None):
        super(DispatcherKeyword, self).__init__(name=name, service=service)
        name = str(name).upper()
        if name in service:
            raise ValueError("keyword named '%s' already in exists." % name)
        self.name = name
        self._acting = False
        self._callbacks = WeakOrderedSet()
        self._history = list()
        self.writeonly = False
        self.readonly = False
        self._period = None
        
        #TODO:
        # Handle XML-specified initial values here.
        self.initial = str(initial)
        
        if period is not None:
            self.period(period)
    
    @property
    def full_name(self):
        """Full name"""
        return "{0}.{1}".format(self.service.name, self.name)
    
    def __contains__ (self, value):
        
        if self.value == None:
            return False
            
        if value in self.value:
            return True
            
        return False
    
    def callback(self, function, remove=False):
        """Register a function to be called whenever this keyword is
        set to a new value."""
        if remove:
            return self._callbacks.discard(function)
        self._callbacks.add(function)
        
    @api_override
    def check(self, value):
        """Check that 'value' is appropriate for this keyword. If it is not, raise a value error."""
        pass
        
    @api_override
    def translate(self, value):
        """Translate a value into a standard representation."""
        return value
        
    def set(self, value, force=False):
        """Set the keyword to the value provided, and broadcast changes.
        
        :param value: The keywrod value.
        :param bool force: Whether to force the change, or ignore repeatedly setting a keyword to the same value.
        """
        value = self.translate(value)
        
        if value == self.value and force is False:
            return
            
        if not (isinstance(value, six.string_types) or value is None):
            raise TypeError("{0}: Value must be string-like, got {1}".format(self, value))
        
        self.check(value)
        
        if value != None:
            self._broadcast(value)
        
        self._history.append(value)
        self.value = value
        
        self._propogate()
        
    @property
    def value(self):
        """Map .value to ._last_value, the cauldron internal location of this variable."""
        return self._last_value
        
    @value.setter
    def value(self, value):
        """Setter for .value"""
        self._last_value = value
        
    @value.deleter
    def value(self):
        """Deleter for .value"""
        self._last_value = None
        
    @abc.abstractmethod
    def _broadcast(self, value):
        """An internal method to be used to actually broadcast the value via the service."""
        pass
        
    @api_override
    def preread(self):
        """Take some action before this value is read. Called at the start of :meth:`update`."""
        pass
        
    @api_override
    def prewrite(self, value):
        """Any actions which need to occur before a value is written. Called to adjust the value in :meth:`modify`.
        
        This can raise :exc:`NoWriteNecessary` if a write is not necessary.
        """
        if self.value == value:
            raise NoWriteNecessary("Value unchanged")
        
        self.check(value)
        return value
    
    @api_override
    def write(self, value):
        """Write the value to the authority source. Called to adjust the value in :meth:`modify`."""
        pass
        
    @api_override
    def read(self):
        """Read the value from the authority source. Called to get the value for :meth:`update`."""
        return self.value
    
    @api_not_implemented
    def schedule(self, appointment=None, cancel=False):
        """Schedule an update."""
        pass
    
    @api_not_implemented
    def period(self, period):
        """How often a keyword should be updated."""
        pass
    
    def _propogate(self):
        """Propagate the change to any waiting callbacks."""
        self._acting = True
        for callback in self._callbacks:
            callback(self)
        self._acting = False
        
    @api_override
    def postwrite(self, value):
        """Take some action post-write."""
        self.set(value)
        
    @api_override
    def postread(self, value):
        """Take some action post-read. Called at the end of :meth:`update`."""
        self.set(value)
        return value
        
    
    def modify(self, value):
        """Modify this keyword's value. This is the public function which should be called to change a keyword value."""
        try:
            value = self.prewrite(value)
        except NoWriteNecessary:
            return
        
        self.write(value)
        self.postwrite(value)
        
    def update(self):
        """Update the value by performing a read. This is the public function which should be called when the keyword is read."""
        self.preread()
        value = self.read()
        
        if value is not None:
            return self.postread(value)
        return value


@six.add_metaclass(abc.ABCMeta)
class DispatcherService(object):
    """A dispatcher is a KTL service server-side. It owns the values."""
    def __init__(self, name, config, setup=None, dispatcher=None):
        super(DispatcherService, self).__init__()
        
        self.dispatcher = dispatcher
        self.name = name.lower()
        
        self._keywords = {}
        self.status_keyword = None
        
        #TODO: Replace the keyword verification done here.
        # self.xml = ktlxml.Service(name, directory=os.path.abspath('./xml/'))
        #
        # self.__contains__ = self.xml.__contains__
        
        # Implementors will be expected to assign Keyword instances
        # for each KTL keyword in this KTL service.
        
        # for keyword in self.xml.list ():
        #     self.__keywords[keyword] = None
        
        if setup is not None:
            setup(self)
        
        self.setupOrphans()
        
        self.begin()
    
    def keywords(self):
        """Return the keywords."""
        keywords = self._keywords.keys()
        keywords.sort()
        return keywords
        
    def setStatusKeyword(self, keyword):
        """Set the status keyword value."""
        keyword = self[keyword]
        if self.status_keyword == keyword:
            return False
        
        self.status_keyword = keyword
        return True
    
    @api_override
    def setupOrphans(self):
        """Set up orphaned keywords, that is keywords which aren't attached to a specific keyword class."""
        pass
    
    def begin(self):
        """Send any queued messages."""
        for keyword in self:
            if keyword is None:
                continue
            if keyword.initial is not None:
                if keyword.value is not None:
                    initial = keyword.value
                else:
                    initial = keyword.initial
                
                try:
                    keyword.set(initial)
                except ValueError as e:
                    self.log(logging.ERROR, "Bad initial value '%s' for '%s'", initial, keyword.name)
                    self.log(logging.ERROR, e)
        
        self._begin()
        
    @abc.abstractmethod
    def _begin(self):
        """Implementation-dependent startup tasks."""
        pass
        
    def __getitem__(self, name):
        """Get a keyword item."""
        try:
            return self._keywords[name.lower()]
        except KeyError:
            return self.__missing__(name.lower())
        
    def __missing__(self, key):
        """What to do with missing keys."""
        raise KeyError("Service {0} has no keyword {1}.".format(self.name, key))
        
    def __setitem__(self, name, value):
        """Set a keyword instance in this server."""
        if not isinstance(value, DispatcherKeyword):
            raise TypeError("value must be a Keyword instance.")
        
        #TODO: Make this work with keyword validation.
        # if name not in self._keywords:
        #     raise KeyError("service '%s' does not have a keyword '%s'" % (self.name, name))
            
        if name in self._keywords and self._keywords[name] is not None:
            raise RuntimeError("cannot set keyword '%s' twice" % (name))
        
        self._keywords[name] = value
        
    def __iter__(self):
        """Iterator over self."""
        return six.itervalues(self._keywords)
    
    def broadcast(self):
        """Called to broadcast all values to ensure that the keyword server matches the keyword inits."""
        for keyword in self:
            value = keyword['value']
            if value != None:
                keyword._broadcast(value)
        
    def keywords(self):
        """The list of available keywords"""
        return list(sorted(self._keywords.keys()))
        
    @api_required
    def shutdown(self):
        """Shutdown this keyword server."""
        pass
        
    def __del__(self):
        """When this service is deleted, shut it down."""
        self.shutdown()

