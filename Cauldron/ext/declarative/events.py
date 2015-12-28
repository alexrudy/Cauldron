# -*- coding: utf-8 -*-
from __future__ import absolute_import

import weakref
import functools
from ...compat import WeakOrderedSet, WeakSet
from ...utils.callbacks import Callbacks

__all__ = ['_DescriptorEvent', '_KeywordEvent', '_KeywordListener']


class _DescriptorEvent(object):
    """Manage events attached to a keyword descriptor."""
    def __init__(self, name, value_as_argument=False, value_as_return=False):
        super(_DescriptorEvent, self).__init__()
        self.name = name
        self.value_as_argument = value_as_argument
        self.value_as_return = value_as_return
        self.callbacks = Callbacks()
        
    def listen(self, func):
        """Listen to a function."""
        self.callbacks.add(func)
        
    def __repr__(self):
        return "<{0} name={1}>".format(self.__class__.__name__, self.name)
    
    def propagate(self, instance, keyword, *args, **kwargs):
        """Propagate a listener event through to the keyword."""
        if self.value_as_argument:
            args = list(args)
            value = args[0]
        else:
            value = None
    
        for callback in self.callbacks:
            if self.value_as_argument:
                args[0] = value
            try:
                returned = callback(keyword, *args, **kwargs)
            except TypeError:
                returned = callback.bound(instance)(keyword, *args, **kwargs)
            if self.value_as_return:
                value = returned
    
        if self.value_as_return:
            return value
        
    def __call__(self, func):
        """Use the event as a descriptor."""
        self.listen(func)
        return func
        
class _KeywordEvent(object):
    """Instrumentation to apply an event to a keyword."""
    
    name = ""
    
    def __new__(cls, keyword, instance, event):
        """Construct or intercept the construction of a keyword event."""
        if isinstance(getattr(keyword, event.name), cls):
            return getattr(keyword, event.name)
        return super(_KeywordEvent, cls).__new__(cls, keyword, instance, event)
    
    def __init__(self, keyword, instance, event):
        super(_KeywordEvent, self).__init__()
        
        func = getattr(keyword, event.name)
        if func is not self:
            self.func = func
            setattr(keyword, event.name, self)
            functools.update_wrapper(self, func)
        if not hasattr(self, 'listeners'):
            self.listeners = []
        listener = _KeywordListener(keyword, instance, event)
        if listener not in self.listeners:
            self.listeners.append(listener)
        self.name = event.name
        self.keyword = weakref.ref(keyword)
        self.value_as_argument, self.value_as_return = event.value_as_argument, event.value_as_return
        
    def __repr__(self):
        return "<{0} name={1} at {2}>".format(self.__class__.__name__, self.name, hex(id(self)))
    
    def __call__(self, *args, **kwargs):
        """This is used to call the underlying method, and to notify listeners."""
        _remove = []
        
        if self.value_as_argument:
            value = args[0]
            args = list(args)
        for callback in self.listeners:
            if self.value_as_argument:
                args[0] = value
            try:
                returned = callback(*args, **kwargs)
            except weakref.ReferenceError:
                _remove.append(callback)
                continue
            if self.value_as_return:
                value = returned
        
        for listener in _remove:
            self.listeners.remove(listener)
        
        # If there are no listeners left, replace the function.
        keyword = self.keyword()
        if not len(self.listeners) and keyword is not None:
            setattr(keyword, self.name, self.func)
        
        if self.value_as_argument:
            args = list(args)
            args[0] = value
        
        return self.func(*args, **kwargs)
        
class _KeywordListener(object):
    """A listener to help fire events on a keyword object."""
    def __init__(self, keyword, instance, event):
        super(_KeywordListener, self).__init__()
        self.event = weakref.proxy(event)
        self.keyword = weakref.proxy(keyword)
        self.instance = weakref.proxy(instance)
    
    def __repr__(self):
        return "<{0} name={1} at {2}>".format(self.__class__.__name__, self.event.name, hex(id(self)))
    
    def __eq__(self, other):
        """Compare to other listeners"""
        if not isinstance(other, _KeywordListener):
            return NotImplemented
        try:
            return (self.event == other.event and self.keyword == other.keyword and self.instance == other.instance)
        except weakref.ReferenceError:
            # Listeners are by definition not equal 
            return False
    
    def __ne__(self, other):
        """Not equal to another listener."""
        eq = self.__eq__(other)
        if eq is NotImplemented:
            return NotImplemented
        return (not eq)
    
    def __call__(self, *args, **kwargs):
        """Ensure that the dispatcher fires before the keyword's own implementation."""
        return self.event.propagate(self.instance, self.keyword, *args, **kwargs)