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

@six.add_metaclass(abc.ABCMeta)
class _BaseKeyword(object):
    """Some common keyword implementation details between the client and dispatcher"""
    
    _ALLOWED_KEYS = None
    _type = str
    
    def __init__(self, service, name, type=None):
        super(_BaseKeyword, self).__init__()
        name = str(name).upper()
        self.service = weakref.proxy(service)
        self.name = name
        self._last_value = None
        self._last_read = None
        self._reading = False
        self._acting = False
        if type is not None:
            self._type = type
        
    def __repr__(self):
        """Represent this keyword"""
        repr_str = "<{0} service={1} name={2}".format(
            self.__class__.__name__, self.service.name, self.name)
        if getattr(self, '_last_value', None) is not None:
            repr_str += " value={value}".format(value=self._last_value)
        return repr_str + ">"
    
    # @property
    # def service(self):
    #     """The parent service for this keyword.
    #
    #     This is retained via weak-reference, so the service may be garbage collected
    #     and destroyed, in which case this property will become ``None``.
    #     """
    #     return self._service()
        
    @property
    def full_name(self):
        """Full name"""
        return "{0}.{1}".format(self.service.name, self.name)
        
    def __getitem__(self, key):
        """Implement the (wacky?) KTL dictionary interface on keywords."""
        if (self._ALLOWED_KEYS is not None and key not in self._ALLOWED_KEYS) or not hasattr(self, '_ktl_{0}'.format(key)):
            raise KeyError("'{0}' has no key '{1}'".format(self, key))
        return getattr(self, '_ktl_{0}'.format(key))()
        
    def _ktl_value(self):
        """Return the keyword value."""
        self._maybe_read()
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
    
    def _maybe_read(self):
        """Maybe perform a read operation, if one is not already in progress."""
        if not self._reading and self._last_value is None:
            self.read()
            
    @contextlib.contextmanager
    def _read(self):
        """Context manager for reading"""
        _reading, self._reading = self._reading, True
        yield
        self._reading = _reading
    
    def _current_value(self, both=False, binary=False):
        """Respond with the current value."""
        with self._read():
            if both:
                return (self._ktl_binary(), self._ktl_ascii())
            if binary:
                return self._ktl_binary()
            return self._ktl_ascii()
    
