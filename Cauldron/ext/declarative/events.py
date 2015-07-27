# -*- coding: utf-8 -*-
from __future__ import absolute_import

import weakref
import functools
from ...compat import WeakOrderedSet, WeakSet

class _DescriptorEvent(object):
    """Manage events attached to a keyword descriptor."""
    def __init__(self, name):
        super(_DescriptorEvent, self).__init__()
        self.name = name
        self.callbacks = WeakOrderedSet()
        
    def listen(self, func):
        """Listen to a function."""
        if not hasattr(func, '_listens'):
            func._listens = WeakSet()
        func._listens.add(self)
        self.callbacks.add(func)
        
    def bind(self, obj):
        """Bind this event to a particular set of instance methods."""
        pass
        
    def __repr__(self):
        return "<{0} name={1}>".format(self.__class__.__name__, self.name)
    
    def propagate(self, obj, keyword, *args, **kwargs):
        """Propagate a listener event through to the keyword."""
        for callback in self.callbacks:
            # This requires an unbound method which should be called as a bound method.
            #TODO: Sleuth method type at runtime.
            callback(obj, keyword, *args, **kwargs)
            
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
        self.listeners.append(_KeywordListener(keyword, instance, event))
        self.name = event.name
        self.keyword = weakref.ref(keyword)
        
    def __repr__(self):
        return "<{0} name={1} at {2}>".format(self.__class__.__name__, self.name, hex(id(self)))
    
    def __call__(self, *args, **kwargs):
        """This is used to call the underlying method, and to notify listeners."""
        _remove = []
        for listener in self.listeners:
            try:
                listener(*args, **kwargs)
            except weakref.ReferenceError:
                _remove.append(listener)
        
        for listener in _remove:
            self.listeners.remove(listener)
        
        # If there are no listeners left, replace the function.
        keyword = self.keyword()
        if not len(self.listeners) and keyword is not None:
            setattr(keyword, self.name, self.func)
        
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
    
    def __call__(self, *args, **kwargs):
        """Ensure that the dispatcher fires before the keyword's own implementation."""
        self.event.propagate(self.instance, self.keyword, *args, **kwargs)