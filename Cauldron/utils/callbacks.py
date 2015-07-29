# -*- coding: utf-8 -*-
"""
Utilities for callback functions
"""

import weakref
import functools
import inspect

__all__ = ['WeakMethod', 'Callbacks']

class WeakMethod(object):
    """A weak reference to a method."""
    
    _instance = lambda : None
    _func = lambda : None
    method = False
    
    def __init__(self, meth):
        super(WeakMethod, self).__init__()
        if not inspect.isroutine(meth):
            raise TypeError("Must be a function or method to create a weak method.")
        self.valid = True
        if hasattr(meth, '__func__'):
            self.func = meth.__func__
        else:
            self.func = meth
        if hasattr(meth, "__self__"):
            self.instance = meth.__self__
            self.method = True
        functools.update_wrapper(self, meth)
        
    def __call__(self, *args, **kwargs):
        """Call the underlying method."""
        return self.get()(*args, **kwargs)
        
    def __hash__(self):
        """The hash value."""
        return (hash(self._func) ^ hash(self._instance)) if self.method else hash(self._func)
        
    def __eq__(self, other):
        """Equality"""
        return (self._func == other._func) and (not self.method or (self._instance == other._instance))
        
    def copy(self):
        return self.__class__(self.get())
    
    @property
    def func(self):
        """The de-referenced function"""
        return self._func()
        
    @func.setter
    def func(self, value):
        """Set the function value."""
        def remove(wr, weakself=weakref.ref(self)):
            self = weakself()
            if self is not None:
                self.valid = False
        self._func = weakref.ref(value, remove)
        
    @property
    def instance(self):
        """The bound instance for bound methods."""
        return self._instance()
        
    @instance.setter
    def instance(self, value):
        """Set the instance."""
        def remove(wr, weakself=weakref.ref(self)):
            self = weakself()
            if self is not None:
                self.valid = False
        self._instance = weakref.ref(value, remove)
        self.method = True
        
    @instance.deleter
    def instance(self):
        """Delete the instance"""
        self._instance = None
        self.method = False
        
    def get(self):
        """Get the bound method."""
        if self.method:
            if self.func is None or self.instance is None:
                raise weakref.ReferenceError("Weak reference to a bound method has expired.")
            return self.func.__get__(self.instance, type(self.instance))
        else:
            if self.func is None:
                raise weakref.ReferenceError("Weak reference to function has expired.")
            return self.func
        return func
        
    def bound(self, instance):
        """Return the bound method."""
        return self.func.__get__(instance, type(instance))
        
    def check(self):
        """Check references here."""
        return self.valid
        

def remove_pending(func):
    """Decorator to remove pending items."""
    @functools.wraps(func)
    def removes(self, *args, **kwargs):
        self._remove_pending()
        return func(self, *args, **kwargs)
    return removes


class IterationGuard(object):
    """An iteration guard context"""
    def __init__(self, container):
        super(IterationGuard, self).__init__()
        self.container = weakref.ref(container)
    
    def __enter__(self):
        w = self.container()
        if w is not None:
            w._iterating.add(self)
        return self
        
    def __exit__(self, e, t, b):
        w = self.container()
        if w is None:
            return
        w._iterating.remove(self)
        if not w._iterating:
            w._remove_pending()
        

class Callbacks(object):
    """A list of callback functions."""
    def __init__(self, *args):
        super(Callbacks, self).__init__()
        self.data = []
        self._pending = []
        self._iterating = set()
        
    def __repr__(self):
        """A callback set."""
        return "<Callbacks {0!r}>".format(self.data)
        
    @remove_pending
    def add(self, item):
        """Add a single item."""
        wm = WeakMethod(item)
        if wm not in self.data:
            self.data.append(wm)
        
    def __iter__(self):
        """Iterate through the list."""
        with IterationGuard(self):
            for r in self.data:
                if r.valid:
                    yield r
                else:
                    self._pending.append(r)
        
    @remove_pending
    def discard(self, item):
        """Discard an item."""
        wm = WeakMethod(item)
        if wm in self.data:
            self.data.remove(wm)
    
    @remove_pending
    def remove(self, item):
        """Remove an item."""
        wm = WeakMethod(item)
        self.data.remove(wm)
    
    def _remove_pending(self):
        """Remove pending items."""
        if self._iterating:
            return
        while self._pending:
            self.data.remove(self._pending.pop())
        
    def __len__(self):
        """Length of the callbacks."""
        return len(self.data) - len(self._pending)
        
    @remove_pending
    def prepend(self, item):
        """Insert an item into the beginning of the callback list."""
        wm = WeakMethod(item)
        if wm in self.data:
            self.data.remove(wm)
        self.data.insert(0, wm)
        
    def __contains__(self, item):
        wm = WeakMethod(item)
        return wm in self.data
        
        