# -*- coding: utf-8 -*-
"""
Base classes relevant to all Cauldron tools.
"""
from __future__ import absolute_import

import six
import abc
import time
import weakref
import contextlib
import threading
import logging

from ..config import get_timeout
from ..utils.callbacks import WeakMethod
from ..utils.helpers import _inherited_docstring

from astropy.utils.misc import InheritDocstrings

class _CauldronBaseMeta(InheritDocstrings, abc.ABCMeta):
    """Combined MetaClass for Cauldron classes."""
    
    def __new__(mcls, name, bases, dct):
        doc = dct.get('__doc__', None)
        if doc is None or doc.strip() == '':
            doc = dct['__doc__'] = _inherited_docstring(*bases)
        return super(_CauldronBaseMeta, mcls).__new__(mcls, name, bases, dct)

class Task(object):
    """A task container for the task queue."""
    
    __slots__ = ('request', 'event', 'result', 'response', 'error', 'callback', 'timeout')
    
    def __init__(self, message, callback, timeout=None):
        super(Task, self).__init__()
        self.request = message
        self.timeout = timeout
        if six.callable(callback):
            self.callback = WeakMethod(callback)
        elif callback is None:
            self.callback = lambda r : r
        else:
            raise TypeError("Expected callback to be callable or None, got {0!r}".format(callback))
        self.response = None
        self.result = None
        self.error = None
        self.event = threading.Event()
        
    def __call__(self):
        """Handle this message."""
        try:
            self.result = self.callback(self.request)
        except Exception as e:
            self.error = e
        self.event.set()
        
    def wait(self, timeout=None):
        """Wait for this task to be finished."""
        if not self.event.isSet():
            self.event.wait(timeout=get_timeout(timeout))
        return self.event.isSet()
    
    def get(self, timeout=None):
        """Get the result."""
        if self.error is not None:
            raise self.error
        if not self.wait(timeout=timeout):
            raise TimeoutError("Task timed out.")
        if self.error is not None:
            raise self.error
        return self.result

@six.add_metaclass(_CauldronBaseMeta)
class _BaseService(object):
    """Common service implementation details between the client and the dispatcher."""
    
    def __init__(self, name):
        super(_BaseService, self).__init__()
        
        #: Service name (string, lower-case)
        self.name = str(name).lower()
        
    def __repr__(self):
        """Represent this object"""
        return "<{0} name='{1}' at {2}>".format(self.__class__.__name__, self.name, hex(id(self)))

@six.add_metaclass(_CauldronBaseMeta)
class _BaseKeyword(object):
    """Some common keyword implementation details between the client and dispatcher"""
    
    _ALLOWED_KEYS = None
    
    service = None
    """The parent :class:`Service` object for this keyword."""
    
    def __init__(self, service, name, type=None):
        super(_BaseKeyword, self).__init__()
        name = str(name).upper()
        self.service = weakref.proxy(service)
        self._name = name
        self._last_value = None
        self._last_read = None
        self._reading = False
        self._acting = False
        if type is not None:
            self._type = type
            
    def _type(self, value):
        """When in doubt, just stringify."""
        return str(value)
        
    def __repr__(self):
        """Represent this keyword"""
        repr_str = "<{0} service={1} name={2}".format(
            self.__class__.__name__, self.service.name, self.name)
        if getattr(self, '_last_value', None) is not None:
            repr_str += " value={value}".format(value=self._last_value)
        return repr_str + ">"
    
    @property
    def name(self):
        """Keyword name."""
        return self._name
    
    @property
    def full_name(self):
        """Full name. Includes Keyword and Service name."""
        return "{0}.{1}".format(self.service.name, self.name)
        
    def __getitem__(self, key):
        """Implement the (wacky?) KTL dictionary interface on keywords."""
        if (self._ALLOWED_KEYS is not None and key not in self._ALLOWED_KEYS) or not hasattr(self, '_ktl_{0}'.format(key)):
            raise KeyError("'{0}' has no key '{1}'".format(self, key))
        return getattr(self, '_ktl_{0}'.format(key))()
        
    def _ktl_value(self):
        """Return the keyword value."""
        return self._last_value
        
    def _ktl_name(self):
        """Keyword name."""
        return self.name.upper()
        
    def _ktl_binary(self):
        """Return the binary value (Native python type.)"""
        return self._type(self._ktl_value())
        
    def _ktl_ascii(self):
        """Return the ascii value (String type.)"""
        return str(self._ktl_value())
    
    def _current_value(self, both=False, binary=False):
        """Respond with the current value."""
        self.service.log.debug("{0!r}._current_value(both={1},binary={2}) = {3!r}".format(
            self, both, binary, self._ktl_value()
        ))
        if both:
            return (self._ktl_binary(), self._ktl_ascii())
        if binary:
            return self._ktl_binary()
        return self._ktl_ascii()
    
