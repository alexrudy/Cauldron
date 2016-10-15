# -*- coding: utf-8 -*-
"""
Implements the abstract-base Keyword and Service classes used for dispatchers. 
This piece of Cauldron is a rough mock of :mod:`DFW`, the dispatcher side interface.
"""

from __future__ import absolute_import

import abc
import six
import weakref
import logging
import warnings
import collections
import time
from ..compat import WeakOrderedSet
from .core import _BaseKeyword, _BaseService
from ..config import read_configuration
from ..exc import CauldronAPINotImplemented, NoWriteNecessary, CauldronXMLWarning, WrongDispatcher, CauldronWarning
from ..utils.helpers import api_not_required, api_not_implemented, api_required, api_override
from ..utils.callbacks import Callbacks
from ..extern import ktlxml
from ..api import STRICT_KTL_XML
from .. import registry

__all__ = ['Keyword', 'Service']

def get_dispatcher_XML(service, name):
    """Check that the XML for the dispatcher is correct.
    
    Checks that if this service has a dispatcher value, that it
    matches the keyword's dispatcher value.
    """
    if service.dispatcher != None:
        keyword_node = service.xml[name]
        dispatcher_node = ktlxml.get.dispatcher(keyword_node)
        dispatcher = ktlxml.get.value(dispatcher_node, 'name')
        return dispatcher
    return None

def get_initial_XML(xml, name):
    """Get the keyword's initial value from the XML configuraton.
    
    :param xml: The XML tree containing keywords.
    :param name: Name of the keyword.
    """
    keyword_xml = xml[name]
    
    initial = None
    
    for element in keyword_xml.childNodes:
        if element.nodeName != 'serverside' and \
           element.nodeName != 'server-side':
            continue
            
        server_xml = element
        
        for element in server_xml.childNodes:
            if element.nodeName != 'initialize':
                continue
                
            # TODO: this loop could check to see if
            # there is more than one initial value,
            # rather than immediately halting the
            # iteration.
            
            try:
                initial = ktlxml.getValue (element, 'value')
            except ValueError: # pragma: no cover
                continue
                
            # Found a value, stop the iteration.
            break
            
            
        if initial != None:
            # Found a value, stop the iteration.
            break
            
    return initial
    
def get_units_xml(xml, name):
    """Get the keyword's units value from the XML configuration."""
    keyword_xml = xml[name]
    
    units = None
    
    try:
        units = ktlxml.getValue(keyword_xml, 'units')
    except ValueError:
        pass
    
    return units

class Keyword(_BaseKeyword):
    """A dispatcher-based keyword, which should own its own values."""
    
    _ALLOWED_KEYS = set(['value', 'name', 'readonly', 'writeonly'])
    
    def __init__(self, name, service, initial=None, period=None):
        name = str(name).upper()
        super(Keyword, self).__init__(name=name, service=service)
        if service.get(name, None) is not None:
            raise ValueError("keyword named '%s' already exists." % name)
        self._acting = False
        self._callbacks = Callbacks()
        self._history = collections.deque(maxlen=100)
        self.writeonly = False
        self.readonly = False
        self._period = None
        self._units = None
        
        try:
            if service.xml is not None:
                dispatcher = get_dispatcher_XML(service, name)
                if dispatcher != service.dispatcher:
                    if STRICT_KTL_XML:
                        raise WrongDispatcher("service dispatcher is '%s', dispatcher for %s is '%s'" % (service.dispatcher, name, dispatcher))
                    warnings.warn(CauldronXMLWarning("Service {0} dispatcher '{1}' does not match keyword {2} dispatcher '{3}'".format(service.name, service.dispatcher, name, dispatcher)))
                
                if initial is None:
                    initial = get_initial_XML(service.xml, name)
        except Exception as e:
            if STRICT_KTL_XML:
                raise
            else:
                warnings.warn("XML setup for keyword '{0}' failed. {1}".format(name, e), CauldronXMLWarning)
        
        # Handle XML-specified initial values here.
        if initial is None:
            self.initial = None
        else:
            self.initial = str(initial)
        
        if period is not None:
            self.period(period)
        
        service[self.name] = self
    
    def __contains__(self, value):
        
        if self.value == None:
            return False
            
        if value in self.value:
            return True
            
        return False
        
    def _ktl_readonly(self):
        """Read only key."""
        return self.readonly
        
    def _ktl_writeonly(self):
        """Write only key."""
        return self.writeonly
    
    def callback(self, function, remove=False):
        """Register a function to be called whenever this keyword is
        set to a new value."""
        if remove:
            return self._callbacks.discard(function)
        self._callbacks.add(function)
        
    @api_override
    def check(self, value):
        """Check that 'value' is appropriate for this keyword. If it is not, raise a value error."""
        pass # pragma: no cover
        
    @api_override
    def translate(self, value):
        """Translate a value into a standard representation."""
        return value
        
    @api_override
    def _get_units(self):
        """Get units from XML"""
        if self.service.xml is not None:
            return get_units_xml(self.service.xml, self.name)
    
    def set(self, value, force=False):
        """Set the keyword to the value provided, and broadcast changes.
        
        :param value: The keyword value.
        :param bool force: Whether to force the change, or ignore repeatedly setting a keyword to the same value.
        """
        value = self.translate(value)
        
        if value == self.value and force is False:
            return
            
        if not (isinstance(value, six.string_types) or value is None):
            raise TypeError("{0}: Value must be string-like, got {1}".format(self, value))
        
        self.check(value)
        
        self._history.append((value, time.time()))
        self.value = value
        
        if value != None:
            self._broadcast(value)
        
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
        pass # pragma: no cover
        
    @api_override
    def preread(self):
        """Take some action before this value is read. Called at the start of :meth:`update`."""
        pass # pragma: no cover
        
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
        pass # pragma: no cover
        
    @api_override
    def read(self):
        """Read the value from the authority source. Called to get the value for :meth:`update`."""
        return self.value
    
    @api_not_implemented
    def schedule(self, appointment=None, cancel=False):
        """Schedule an update."""
        pass # pragma: no cover
    
    @api_not_implemented
    def period(self, period):
        """How often a keyword should be updated."""
        pass # pragma: no cover
    
    def _propogate(self):
        """Propagate the change to any waiting callbacks."""
        if not self._acting:
            try:
                self._acting = True
                self._callbacks(self)
            finally:
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


class Service(_BaseService):
    """A dispatcher is a KTL service server-side.
    
    A class encapsulating a basic representation of a complete KTL service. The `name` argument is case sensitive, and will be used to locate (and load) the service's KTLXML representation. The `config` argument specifies the stdiosvc configuration file that will be used when loading the stdiosvc front-end. The `setup` function will be called to properly instantiate all keywords associated with this :class:`Service` instance; it accepts a :class:`Service` instance as its sole argument, and should instantiate :class:`Keyword.Basic` objects directly. If any keywords are not instantiated, they will be given placeholder "cacheing" :class:`Keyword.Basic` instances of the appropriate type (string, integer, etc.). See :func:`setupOrphans` for an example. If `dispatcher` is specified, only keywords corresponding to that dispatcher number will be instantiated.
    
    Parameters
    ----------
    name : str
        the Service name.
    
    config : str
        the stdiosvc configuration filename, or the Cauldron configuration filename.
    
    setup : callable
        a function which will be called to set up the keywords for this service.
    
    dispatcher : str, optional
        The name of the dispatcher to use for this service. If not provided, all keywords will be used.
    
    """
    
    name = None
    _DISPATCHER = True
    
    def __init__(self, name, config, setup=None, dispatcher=None):
        super(Service, self).__init__(name=name)
        
        self._config = read_configuration(config)
        self._configuration_location = config if isinstance(config, six.string_types) else "???"
        self.dispatcher = dispatcher if dispatcher else "DEFAULT"
        self.log = logging.getLogger("DFW.Service.{0}".format(self.name))
        self.log.info("Starting Service '{0}' using backend '{1}'".format(self.name, registry.dispatcher.backend))
        
        self._keywords = {}
        self.status_keyword = None
        
        try:
            self.xml = ktlxml.Service(self.name)
        except Exception as e:
            if STRICT_KTL_XML:
                raise
            warning = CauldronXMLWarning("KTLXML was not loaded correctly. Keywords will not be validated against XML. Exception was {0!s}.".format(e))
            warnings.warn(warning)
            self.log.warning(str(warning))
            self.xml = None
        else:
            # Implementors will be expected to assign Keyword instances
            # for each KTL keyword in this KTL service.
            for keyword in self.xml.list():
                if self.dispatcher == get_dispatcher_XML(self, keyword):
                    self._keywords[keyword] = None
        
        self._prepare()
        
        if setup is not None:
            setup(self)
        
        if self._config.getboolean("core","setupOrphans"):
            self.setupOrphans()
        
        self.begin()
    
    @property
    def _Keyword_cls(self):
        """Get the keyword class."""
        from Cauldron import DFW
        return DFW.Keyword.Keyword
    
    def keywords(self):
        """The list of available keywords"""
        return list(sorted(self._keywords.keys()))
        
    def setStatusKeyword(self, keyword):
        """Set the status keyword value."""
        keyword = self[keyword]
        if self.status_keyword == keyword:
            return False
        
        self.status_keyword = keyword
        return True
    
    def setupOrphans(self):
        """Set up orphaned keywords, that is keywords which aren't attached to a specific keyword class."""
        for name, keyword in self._keywords.items():
            if keyword is None:
                dispatcher = get_dispatcher_XML(self, name)
                if dispatcher == self.dispatcher:
                    self._setupOrphan(name)
    
    def _setupOrphan(self, name):
        """Set up a single orphan."""
        from Cauldron import DFW
        try:
            xml = self.xml[name]
            ktl_type = ktlxml.getValue(xml, 'type')
            cls = DFW.Keyword.types[ktl_type]
        except Exception as e:
            if STRICT_KTL_XML:
                raise
            warnings.warn(CauldronXMLWarning("XML setup for orphan keyword {0} failed: {1}".format(name, str(e))))
            cls = DFW.Keyword.Keyword
        
        try:
            cls(name, service=self)
        except WrongDispatcher:
            pass
        else:
            warnings.warn(CauldronWarning("Set up an orphaned keyword {0} for service {1} dispatcher {2}".format(
                name, self.name, self.dispatcher
            )))
    
    @api_override
    def _prepare(self):
        """This method is called once the configuration has been read, but before setup. It provides an implementation-dependent way to take action after the system has been configured, but before any keywords are available."""
        pass
    
    def begin(self):
        """Send any queued messages."""
        for keyword in self:
            if keyword is None:
                continue
            if keyword.initial is not None:
                
                # Ensure that if this keyword was already written to,
                # we don't overwrite the already written value.
                if keyword.value is not None:
                    initial = keyword.value
                else:
                    initial = keyword.initial
                
                try:
                    keyword.set(initial)
                except ValueError as e:
                    self.log.error("Bad initial value '%s' for '%s'", initial, keyword.name)
                    self.log.error(str(e))
        
        self._begin()
        
    @abc.abstractmethod
    def _begin(self):
        """Implementation-dependent startup tasks should be handled here. This method is called
        when :meth:`begin` is done setting initial keyword values."""
        pass # pragma: no cover
        
    def __getitem__(self, name):
        """Get a keyword item."""
        name = str(name).upper()
        try:
            keyword = self._keywords[name]
        except KeyError:
            return self.__missing__(name)
        if keyword is None:
            return self.__missing__(name)
        return keyword
        
    def __missing__(self, key):
        """What to do with missing keys."""
        return self._Keyword_cls(key, self)
    
    def __setitem__(self, name, value):
        """Set a keyword instance in this server."""
        if not isinstance(value, Keyword):
            raise TypeError("value must be a Keyword instance.")
        
        name = str(name).upper()
        
        if name not in self._keywords:
            if not STRICT_KTL_XML:
                if self.xml is not None:
                    warnings.warn(CauldronXMLWarning("service '{0}' does not have a keyword '{1}' in XML".format(self.name, name)))
            else:
                raise KeyError("service '%s' does not have a keyword '%s'" % (self.name, name))
            
        if name in self._keywords and self._keywords[name] is not None:
            raise RuntimeError("cannot set keyword '%s' twice" % (name))
        
        self._keywords[name] = value
        
    def __contains__(self, name):
        """Check for name in self"""
        if self.xml is not None:
            return (str(name).upper() in self.xml and STRICT_KTL_XML) or (str(name).upper() in self._keywords and not STRICT_KTL_XML)
        return str(name).upper() in self._keywords
        
    def __iter__(self):
        """Iterator over self."""
        return six.itervalues(self._keywords)
    
    def get(self, name, default=None):
        """Get a keyword."""
        return self._keywords.get(str(name).upper(), default)
    
    def broadcast(self):
        """Called to broadcast all values to ensure that the keyword server matches the keyword."""
        for keyword in self:
            value = keyword['value']
            if value != None:
                keyword._broadcast(value)
        
    @api_required
    def shutdown(self):
        """Shutdown this keyword server."""
        pass # pragma: no cover
        
    def __del__(self):
        """When this service is deleted, shut it down."""
        self.shutdown()

