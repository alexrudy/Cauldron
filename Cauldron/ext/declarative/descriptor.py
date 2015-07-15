# -*- coding: utf-8 -*-
"""
Implement the declarative descriptor.
"""
from __future__ import absolute_import

import functools
import weakref
from .events import _DescriptorEvent, _KeywordListener

__all__ = ['KeywordDescriptor', 'DescriptorBase']

def descriptor__get__(f):
    """A getter for descriptors."""
    @functools.wraps(f)
    def dfunc(self, obj, objtype=None):
        if obj is None:
            return self
        return f(self, obj, objtype)
    return dfunc
    
class DescriptorBase(object):
    """A keyword descriptor base class which assists in binding descriptors to keywords."""
    
    @classmethod
    def _keyword_descriptors(cls):
        """Find all of the keyword descriptors."""
        for var in dir(cls):
            try:
                member = getattr(cls, var)
                if isinstance(member, KeywordDescriptor):
                    yield member
            except:
                # We don't know what happened here, but there are lots of ways
                # to override class-level attribute access and screw this up.
                pass
            
    def bind(self, service):
        """Bind a service to the descriptors in this class."""
        cls = self.__class__
        for desc in self._keyword_descriptors():
            desc.bind(self, service)

class KeywordDescriptor(object):
    """A descriptor which maintains a relationship with a keyword.
    
    The descriptor should be used as a class level variable. It can be accessed as
    a regular instance variable, where it will return the result of :func:`update`
    operations. Setting the instance variable will result in a modify operation.
    """
    
    _EVENTS = ['preread', 'read', 'postread', 'prewrite', 'write', 'postwrite', 'check']
    
    def __init__(self, name, initial=None, type=lambda v : v, doc=None, readonly=False, writeonly=False):
        super(KeywordDescriptor, self).__init__()
        self.name = name.upper()
        self.initial = initial
        self.type = type
        self.__doc__ = doc
        if readonly and writeonly:
            raise ValueError("Keyword {0} cannot be 'readonly' and 'writeonly'.".format(self.name))
        self.readonly = readonly
        self.writeonly = writeonly
        for event in self._EVENTS:
            setattr(self, event, _DescriptorEvent(event))
        self.callback = _DescriptorEvent("_propogate")
        
    @descriptor__get__
    def __get__(self, obj, objtype=None):
        """Getter"""
        return self.type(self.keyword(obj).update())
        
    def __set__(self, obj, value):
        """Set the value."""
        return self.keyword(obj).modify(self.type(value))
        
    def bind(self, obj, service):
        """Bind a service to this instance."""
        obj._service = weakref.ref(service)
        for event_name in self._EVENTS:
            event = getattr(self, event_name)
            event.listeners[obj] = _KeywordListener(service[self.name], obj, event)
        self.callback.listeners[obj] = _KeywordListener(service[self.name], obj, self.callback)
        
        
    def keyword(self, obj):
        """Get the Keyword instance."""
        return obj._service()[self.name]
        

    