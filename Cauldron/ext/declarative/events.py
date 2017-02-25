# -*- coding: utf-8 -*-
from __future__ import absolute_import

import weakref
import functools
from ...compat import WeakOrderedSet, WeakSet
from ...utils.callbacks import Callbacks
from ...utils import ReferenceError

__all__ = ['_DescriptorEvent', '_KeywordEvent', '_KeywordListener']


class _DescriptorEvent(object):
    """Manage events attached to a keyword descriptor."""
    def __init__(self, name, replace_method=False):
        super(_DescriptorEvent, self).__init__()
        self.name = name
        self.replace_method = replace_method
        self.callbacks = Callbacks()
        
    def listen(self, func):
        """Listen to a function."""
        self.callbacks.add(func)
        if self.replace_method and len(self.callbacks) > 1:
            raise ValueError("There is more than one replacement for '{0}'".format(self.name))
        
    def __repr__(self):
        return "<{0} name={1}>".format(self.__class__.__name__, self.name)
    
    def propagate(self, instance, keyword, *args, **kwargs):
        """Propagate a listener event through to the keyword."""
        returned = None
        for callback in self.callbacks:
            try:
                returned = callback(keyword, *args, **kwargs)
            except (TypeError, ReferenceError):
                returned = callback.bound(instance)(keyword, *args, **kwargs)
        
        return returned
        
    def __call__(self, func):
        """Use the event as a descriptor."""
        self.listen(func)
        return func
        
class _KeywordEvent(object):
    """Instrumentation to apply an event to a keyword."""
    
    name = ""
    replace_method = False
    func = None
    
    def __new__(cls, keyword, instance, event):
        """Construct or intercept the construction of a keyword event."""
        if isinstance(getattr(keyword, event.name, None), cls):
            return getattr(keyword, event.name)
        return super(_KeywordEvent, cls).__new__(cls)
    
    def __init__(self, keyword, instance, event):
        super(_KeywordEvent, self).__init__()
        
        # Important implementation note here: this object behaves like a singleton
        # due to the override in __new__ above, this method will be called on both
        # new objects and already existing objects which are re-bound to a particular
        # function. The re-binding allows us to add additional listeners to this
        # object on an as-needed basis. However, everything done in this method
        # should be ok with multiple invocations.
        
        func = getattr(keyword, event.name, None)
        
        if func is not None and func is not self:
            functools.update_wrapper(self, func)
        
        if func is not self:
            self.func = func
            setattr(keyword, event.name, self)
        
        if event.name == "_propogate" and func is None:
            keyword.callback(self.__call__)
        
        if not hasattr(self, 'listeners'):
            self.listeners = []
        listener = _KeywordListener(keyword, instance, event)
        if listener not in self.listeners:
            self.listeners.append(listener)
        if event.replace_method and self.nlisteners > 1:
            msg_callbacks = ",".join([repr(cb) for l in self.listeners for cb in l.event.callbacks])
            raise ValueError("There are {0:d} method replacements "
                 "(in {1:d} listeners) for '{2:s}' on keyword "
                 "'{3:s}': [{4:s}]".format(self.nlisteners, len(self.listeners), 
                                           event.name, keyword.name, msg_callbacks))
        
        self.replace_method |= event.replace_method
        self.name = event.name
        self.keyword = weakref.ref(keyword)
        
    @property
    def nlisteners(self):
        """Number of listening callbacks."""
        return sum(len(listener.event.callbacks) for listener in self.listeners)
        
    def __repr__(self):
        return "<{0} name={1} at {2}>".format(self.__class__.__name__, self.name, hex(id(self)))
    
    def __call__(self, *args, **kwargs):
        """This is used to call the underlying method, and to notify listeners."""
        _remove = []
        returned = None
        for callback in self.listeners:
            try:
                returned = callback(*args, **kwargs)
            except ReferenceError:
                _remove.append(callback)
                continue
            
        for listener in _remove:
            self.listeners.remove(listener)
        
        # If there are no listeners left, replace the function.
        keyword = self.keyword()
        if not len(self.listeners) and keyword is not None:
            setattr(keyword, self.name, self.func)
        
        if self.replace_method and self.nlisteners:
            return returned
        elif self.func is not None:
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
        except ReferenceError:
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