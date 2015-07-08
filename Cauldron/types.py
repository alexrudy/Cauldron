# -*- coding: utf-8 -*-
"""
Keywords can have differing python types.

This module implements those types in a way that meshes well with the parent modules.
"""

from __future__ import absolute_import

import warnings
import types
import sys
import abc
import six
from .exc import CauldronAPINotImplementedWarning
from .api import _guard_use, get_client, get_dispatcher, register_dispatcher_setup, register_client_setup

__all__ = ['Basic', 'Keyword', 'Boolean', 'Double', 'Float', 'Integer', 'Enumerated', 'Mask', 'String', 'IntegerArray', 'FloatArray', 'DoubleArray']


_dispatcher = set()
def dispatcher_keyword(cls):
    """A decorator to mark classes which should also be exposed in the ktl.Keyword module."""
    _dispatcher.add(cls)
    return cls

_client = set()
def client_keyword(cls):
    """A decorator to mark classes which should also be exposed in the ktl.Keyword module."""
    _client.add(cls)
    return cls
    
def generate_keyword_subclasses(basecls, subclasses):
    """Given a base class, generate keyword subclasses."""
    for subclass in subclasses:
        yield type(subclass.__name__, (subclass, basecls), dict())

@register_client_setup
def setup_client_keyword_module():
    """Generate the Keyword module"""
    _guard_use("setting up the ktl.Keyword module")
    _, basecls = get_client()
    from ._ktl import Keyword
    for kwcls in generate_keyword_subclasses(basecls, _client):
        setattr(Keyword, kwcls.__name__, kwcls)
        Keyword.__all__.append(kwcls.__name__)
    
@register_dispatcher_setup
def setup_dispatcher_keyword_module():
    """Set up the Keyword module"""
    _guard_use("setting up the DFW.Keyword module")
    _, basecls = get_dispatcher()
    from ._DFW import Keyword
    for kwcls in generate_keyword_subclasses(basecls, _client):
        setattr(Keyword, kwcls.__name__, kwcls)
        Keyword.__all__.append(kwcls.__name__)

@six.add_metaclass(abc.ABCMeta)
class _MetaClassFix(object): pass
        

class _NotImplemented(_MetaClassFix):
    """An initializer for not-yet implemented keywords which emits a warning."""
    def __init__(self, *args, **kwargs):
        warnings.warn("{0} Keywords aren't yet implemented. Defaulting to a {1} keyword.".format(self.__class__.__name__, self.__class__.__mro__[1].__name__),
             CauldronAPINotImplementedWarning)
        super(_NotImplemented, self).__init__(*args, **kwargs)

@dispatcher_keyword
class Basic(_MetaClassFix): pass

@dispatcher_keyword
@client_keyword
class Keyword(Basic): pass

@dispatcher_keyword
@client_keyword
class Boolean(Keyword):
    """A boolean-valued keyword."""
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
            raise ValueError("Booleans must have ascii values of '0' or '1'.")
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
    """Double values."""
    _type = float
    
@dispatcher_keyword
class Float(Double): pass

@client_keyword
class Numeric(Double): pass

@dispatcher_keyword
@client_keyword
class Integer(Basic):
    
    _type = int
    
    minimum = -pow(2, 31)
    maximum = pow(2, 31) - 1
    
    def cast(self, value):
        """Cast through float"""
        return int(float(value))
    
    def check(self, value):
        """Check range against allowed KTL values."""
        super(Integer, self).check(value)
        if not (self.minimum < value < self.maximum):
            raise ValueError("Keyword {0} must have integer values in range {1} to {2}".format(self.name, self.minimum, self.maximum))
        
    def increment(self, amount=1):
        """Increment the integer value."""
        value = int(self.value) if self.value is not None else 0
        self.set(str(value + int(amount)))
        

@dispatcher_keyword
class Enumerated(Integer, _NotImplemented):
    pass
    

@dispatcher_keyword
class Mask(Basic, _NotImplemented):
    pass

@dispatcher_keyword
@client_keyword
class String(Basic): pass

@dispatcher_keyword
class IntegerArray(Basic, _NotImplemented): pass

@dispatcher_keyword
class DoubleArray(Basic, _NotImplemented): pass

@dispatcher_keyword
class FloatArray(DoubleArray): pass


