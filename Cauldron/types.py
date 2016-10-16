# -*- coding: utf-8 -*-
"""
Keywords can have differing python types. The types provide validation and sanitization
for keyword values.

In the KTL python API, keyword types are implemented separately for clients and dispatchers. In this module,
a single class heirarchy is implemented for clients and dispatchers. Keyword types override parent class methods
to provide the necessary behavior, though at a minimum, Keyword types simply set the ``_type`` class attribute
to a python type.
"""

from __future__ import absolute_import

import warnings
import collections
import itertools
import types
import sys
import abc
import six
import logging
from .exc import CauldronAPINotImplementedWarning, CauldronXMLWarning, CauldronTypeError
from .api import guard_use, STRICT_KTL_XML, BASENAME, CAULDRON_SETUP
from .base.core import _CauldronBaseMeta
from .extern import ktlxml
from . import registry
from .utils.helpers import _inherited_docstring, _prepend_to_docstring

__all__ = ['KeywordType', 'Basic', 'Keyword', 'Boolean', 'Double', 'Float', 'Integer', 'Enumerated', 'Mask', 'String', 'IntegerArray', 'FloatArray', 'DoubleArray', 'dispatcher_keyword', 'client_keyword', 'ClientKeywordType', 'DispatcherKeywordType']

log = logging.getLogger(__name__)

_dispatcher = set()
def dispatcher_keyword(cls):
    """A decorator to mark classes which should also be exposed in the DFW.Keyword module."""
    _dispatcher.add(cls)
    return cls

_client = set()
def client_keyword(cls):
    """A decorator to mark classes which should also be exposed in the ktl.Keyword module."""
    _client.add(cls)
    return cls
    
_bases = set()

def _generate_keyword_subclass(basecls, subclass, module):
    """Generate a single keyword subclass."""
    if getattr(subclass, '__doc__', None) is not None:
        doc = _prepend_to_docstring(_inherited_docstring(basecls), subclass.__doc__)
    else:
        doc = _inherited_docstring(basecls)
    cls = type(subclass.__name__, (subclass, basecls),
        {'__module__':module, '__doc__':doc})
    cls.KTL_REGISTERED = True
    subclass._subcls = cls
    return cls
    
def generate_keyword_subclasses(basecls, subclasses, module):
    """Given a base class, generate keyword subclasses."""
    for subclass in subclasses:
        yield _generate_keyword_subclass(basecls, subclass, module)

def _setup_keyword_class(kwcls, module):
    """Set up a keyword class on a module."""
    if kwcls.KTL_REGISTERED:
        module.types[kwcls.KTL_TYPE] = kwcls
        for alias in kwcls.KTL_ALIASES:
            module.types[alias] = kwcls
        if not hasattr(module, kwcls.__name__):
            # Don't replace already existing keywords.
            setattr(module, kwcls.__name__, kwcls)
            module.__all__.append(kwcls.__name__)


@registry.client.setup_for('all')
def setup_client_keyword_module():
    """Generate the Keyword module"""
    guard_use("setting up the ktl.Keyword module")
    basecls = registry.client.Keyword
    from .ktl import Keyword
    for kwcls in generate_keyword_subclasses(basecls, _client, module="{0}.ktl.Keyword".format(BASENAME)):
        _setup_keyword_class(kwcls, Keyword)
    Keyword.__all__ = list(set(Keyword.__all__))
    
@registry.dispatcher.setup_for('all')
def setup_dispatcher_keyword_module():
    """Set up the Keyword module"""
    guard_use("setting up the DFW.Keyword module")
    basecls = registry.dispatcher.Keyword
    from .DFW import Keyword
    for kwcls in generate_keyword_subclasses(basecls, _dispatcher, module="{0}.DFW.Keyword".format(BASENAME)):
        _setup_keyword_class(kwcls, Keyword)
    Keyword.__all__ = list(set(Keyword.__all__))
    
@registry.dispatcher.teardown_for('all')
@registry.client.teardown_for('all')
def teardown_generated_user_classes():
    """Cleanup user generated classes."""
    for cls in _bases:
        if hasattr(cls, '_subcls'):
            del cls._subcls
    _bases.clear()

@six.add_metaclass(_CauldronBaseMeta)
class KeywordType(object):
    """A base class for all subclasses of KTL Keyword which implement a type specialization.
    
    The name of each type specialization is available as the :attr:`KTL_TYPE` class attribute.
    """
    KTL_TYPE = None
    """The KTL-API type name corresponding to this class."""
    
    KTL_REGISTERED = False
    """Flag which determines if this subclass is a KTL-registered subclass."""
    
    KTL_ALIASES = ()
    """A list of additional KTL-API type names that can be used with this class."""
    
    _subcls = None
    
    @classmethod
    def _is_dispatcher(cls, args, kwargs):
        """Get the service argument."""
        if "service" in kwargs:
            return getattr(kwargs["service"],'_DISPATCHER', None)
        for i,arg in enumerate(args):
            if i > 1:
                break
            if not isinstance(arg, six.string_types):
                return getattr(arg, '_DISPATCHER', None)
        return None
    
    @classmethod
    def _get_cauldron_basecls(cls, dispatcher=None):
        """Get the Cauldron basecls."""
        if dispatcher is None:
            raise RuntimeError("Generic KeywordType shouldn't try to subclass itself.")
        elif dispatcher is True:
            registry.dispatcher.guard("initializing any keyword objects.")
            return registry.dispatcher.Keyword
        else:
            registry.client.guard("initializing any keyword objects.")
            return registry.client.Keyword
        
    @classmethod
    def _make_subclass(cls, basecls):
        """Make a Cauldron subclass."""
        if cls.__dict__.get('_subcls',None) is None:
            cls._subcls = type(cls.__name__, (cls, basecls), {'__module__':cls.__module__, '__doc__':cls.__doc__})
            _bases.add(cls)
        return cls._subcls
    
    def __new__(cls, *args, **kwargs):
        if not cls.KTL_REGISTERED:
            dispatcher = cls._is_dispatcher(args, kwargs)
            basecls = cls._get_cauldron_basecls(dispatcher)
            if not issubclass(cls, basecls):
                newcls = cls._make_subclass(basecls)
                return newcls.__new__(newcls, *args, **kwargs)
        
        # See http://stackoverflow.com/questions/19277399/why-does-object-new-work-differently-in-these-three-cases for why this is necessary.
        # Basically, because some child may override __new__, we must override it here to never pass arguments to the object.__new__ method.
        if super(KeywordType, cls).__new__ is object.__new__:
            return super(KeywordType, cls).__new__(cls)
        return super(KeywordType, cls).__new__(cls, *args, **kwargs)
    
    def __init__(self, *args, **kwargs):
        super(KeywordType, self).__init__(*args, **kwargs)
        if self.KTL_TYPE is None:
            raise CauldronTypeError("Keyword {0} cannot have KTL type = None".format(self.name))
    
    def _ktl_type(self):
        """Return the ktl type of this key."""
        return "KTL_{0:s}".format(self.KTL_TYPE.upper())

class DispatcherKeywordType(KeywordType):
    """Keyword type for dispatchers."""
    
    @classmethod
    def _get_cauldron_basecls(cls, dispatcher):
        """Get the Cauldron basecls."""
        assert dispatcher in (None, True)
        registry.dispatcher.guard("initializing any keyword objects.")
        return registry.dispatcher.Keyword
    
class ClientKeywordType(KeywordType):
    """Keyword type for ktl clients."""
    
    @classmethod
    def _get_cauldron_basecls(self, dispatcher):
        """Get the Cauldron basecls."""
        assert dispatcher in (None, False)
        registry.client.guard("initializing any keyword objects.")
        return registry.client.Keyword

class _NotImplemented(KeywordType):
    """An initializer for not-yet implemented keywords which emits a warning."""
    def __init__(self, *args, **kwargs):
        warnings.warn("{0} Keywords aren't yet implemented. Defaulting to a {1} keyword.".format(self.__class__.__name__, self.__class__.__mro__[1].__name__),
             CauldronAPINotImplementedWarning)
        super(_NotImplemented, self).__init__(*args, **kwargs)

@dispatcher_keyword
class Basic(KeywordType):
    """The base class for KTL and DFW keywords."""
    KTL_TYPE = 'basic'
    

@dispatcher_keyword
@client_keyword
class Keyword(Basic): 
    """An alias for :class:`Basic`"""
    pass

@dispatcher_keyword
@client_keyword
class Boolean(Basic):
    """A boolean-valued keyword."""
    KTL_TYPE = 'boolean'
    
    mapping = {True: '1',
           '1': '1',
           'true': '1',
           't': '1',
           'yes': '1',
           'on': '1',
           
           False: '0',
           '0': '0',
           'false': '0',
           'f': '0',
           'no': '0',
           'off': '0'}
    
    def _type(self, value):
        """Return the python type for a value."""
        if value not in '01':
            raise ValueError("Booleans must have ascii values of '0' or '1'. Bad value {0!r}".format(value))
        return value == '1'
    
    def translate(self, value):
        """Translate the value."""
        try:
            return self.mapping[value]
        except KeyError:
            try:
                return self.mapping[value.lower()]
            except (AttributeError, KeyError):
                pass
        raise ValueError("Keyword {0} only accepts valid boolean values. Bad value {1!r}".format(self.name, value))
        
    def prewrite(self, value):
        """Check value before writing."""
        return super(Boolean, self).prewrite(self.translate(value))
        
@dispatcher_keyword
class Double(Basic):
    """A numerical value keyword."""
    KTL_TYPE = 'double'
    _type = float
    
    def translate(self, value):
        """Translate the value into something we can deal with."""
        return str(float(value))
        
    def postread(self, value):
        """Post read """
        return super(Double, self).postread(self._type(value))
    
@dispatcher_keyword
class Float(Double):
    """A numerical value keyword."""
    KTL_TYPE = 'float'

@client_keyword
class Numeric(Double):
    """A numerical value keyword."""
    KTL_ALIASES = ('float',)

@dispatcher_keyword
@client_keyword
class Integer(Basic):
    """An integer value keyword."""
    KTL_TYPE = 'integer'
    _type = int
    
    minimum = -pow(2, 31)
    maximum = pow(2, 31) - 1
    
    def cast(self, value):
        """Cast through float"""
        return int(float(value))
    
    def check(self, value):
        """Check range against allowed KTL values."""
        if not (self.minimum < self.cast(value) < self.maximum):
            raise ValueError("Keyword {0} must have integer values in range {1} to {2}".format(self.name, self.minimum, self.maximum))
        super(Integer, self).check(value)
        
    def increment(self, amount=1):
        """Increment the integer value."""
        value = self.cast(self.value) if self.value is not None else 0
        self.set(str(value + int(amount)))
        
    def translate(self, value):
        """Check value before writing."""
        return str(self.cast(value))
        
    def postread(self, value):
        """Translate the value for python binary return."""
        return super(Integer, self).postread(self.cast(value))
        

class _EnumerationValues(collections.Mapping):
    """A mapping goes both directions through a dictionary."""
    def __init__(self, source):
        super(_EnumerationValues, self).__init__()
        self.source = source
        
    def __iter__(self):
        return iter(self.source.enums)
        
    def __len__(self):
        return len(self.source.enums)
    
    def __contains__(self, key):
        return self.source.enums.__contains__(key)
    
    def __getitem__(self, key):
        if key not in self.source.enums:
            raise KeyError(key)
        else:
            return self.source[key]
            
    def __setitem__(self, key, value):
        self.source[value] = key

class Enumeration(dict):
    """The key-value pairs for enumeration"""
    def __init__(self, *args, **kwargs):
        super(Enumeration, self).__init__()
        self.enums = set()
        self.bkeys = set()
        for k, v in dict(*args, **kwargs).items():
            self[k] = v
        
    def __setitem__(self, key, value):
        value = str(value)
        skey = str(key)
        super(Enumeration, self).__setitem__(skey, value)
        super(Enumeration, self).__setitem__(value, skey)
        super(Enumeration, self).__setitem__(value.lower(), skey)
        try:
            key = int(key)
        except (TypeError, ValueError) as e:
            pass
        else:
            super(Enumeration, self).__setitem__(key, value)
            self.bkeys.add(key)
        self.enums.add(value.lower())
    
    def load_from_xml(self, xml):
        """Load enumeration values from XML"""
        
        values = None
        
        for entry in xml.childNodes:
            if entry.nodeName == 'values':
                values = entry
        
        if values != None:
            for entry in values.childNodes:
                if entry.nodeName == 'entry':
                    key   = ktlxml.getValue (entry, 'key')
                    value = ktlxml.getValue (entry, 'value')
                    self[key] = value
        

@dispatcher_keyword
class Enumerated(Integer):
    """An enumerated keyword, which uses an integer as the underlying datatype."""
    KTL_TYPE = 'enumerated'
    
    def __init__(self, *args, **kwargs):
        # We override __init__ so we can set up 
        # the enumerated values.
        super(Enumerated, self).__init__(*args, **kwargs)
        self.mapping = Enumeration()
        self.values = _EnumerationValues(self.mapping)
        
        try:
            xml = self.service.xml[self.name]
            self.mapping.load_from_xml(xml)
        except Exception as e:
            if STRICT_KTL_XML:
                raise
            warnings.warn("XML enumeration setup for keyword '{0}' failed. {1}".format(self.name, e), CauldronXMLWarning)
        
    @property
    def keys(self):
        """The keys available."""
        return self.mapping.enums
        
    def prewrite(self, value):
        return super(Enumerated, self).prewrite(self.translate(value))
    
    def translate(self, value):
        """Translate to the enumerated value"""
        if str(value).lower() in self.keys:
            value = str(value).lower()
        elif str(value).lower() in self.mapping:
            value = self.mapping[str(value).lower()]
        else:
            raise ValueError("Bad value for enumerated keyword {0}: '{1}' not in {2!r}".format(self.full_name, value, self.mapping))
        return value

@dispatcher_keyword
class Mask(Basic, _NotImplemented):
    KTL_TYPE = 'mask'

@dispatcher_keyword
@client_keyword
class String(Basic): 
    """An ASCII valued keyword, implemented identically to :class:`Basic`."""
    KTL_TYPE = 'string'

@dispatcher_keyword
class IntegerArray(Basic, _NotImplemented):
    KTL_TYPE = 'integer array'

@dispatcher_keyword
class DoubleArray(Basic, _NotImplemented):
    KTL_TYPE = 'double array'

@dispatcher_keyword
class FloatArray(DoubleArray):
    KTL_TYPE = 'float array'
