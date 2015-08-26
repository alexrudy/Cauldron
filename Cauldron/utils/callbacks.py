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
    callback = None
    _valid = False
    
    def __init__(self, meth, callback=None):
        super(WeakMethod, self).__init__()
        if not inspect.isroutine(meth):
            raise TypeError("Must be a function or method to create a weak method.")
        self._valid = True
        if hasattr(meth, '__func__'):
            self.func = meth.__func__
        else:
            self.func = meth
        if hasattr(meth, "__self__"):
            if meth.__self__ is not None:
                self.instance = meth.__self__
            self.method = True
        functools.update_wrapper(self, meth)
        self.callback = callback
        
    def __call__(self, *args, **kwargs):
        """Call the underlying method."""
        return self.get()(*args, **kwargs)
        
    def __hash__(self):
        """The hash value."""
        if not self.valid:
            return super(WeakMethod, self).__hash__()
        return (hash(self._func) ^ hash(self._instance)) if self.method else hash(self._func)
        
    def __eq__(self, other):
        """Equality"""
        if not isinstance(other, self.__class__): #pragma: no cover
            return False
        if not (self.valid and other.valid):
            return False
        return (self._func == other._func) and (not self.method or (self._instance == other._instance))
        
    def copy(self):
        return self.__class__(self.get())
    
    @property
    def valid(self):
        """Is this reference still valid?"""
        return self._valid
        
    @valid.setter
    def valid(self, value):
        """Set the valid flag."""
        self._valid = bool(value)
        if (not self._valid) and (self.callback is not None):
            self.callback(self)
    
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
        if w is None: #pragma: no cover
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
        for item in args:
            self.add(item)
        
    def __repr__(self):
        """A callback set."""
        return "<Callbacks {0!r}>".format(self.data)
        
    def _with_removing_callback(self, item):
        """Return a weak method with a removing callback"""
        def _remove(wr, selfref=weakref.ref(self)):
            self = selfref()
            if self is not None:
                if self._iterating:
                    self._pending.append(wr)
                else:
                    self.data.remove(wr)
        return WeakMethod(item, _remove)
        
    @remove_pending
    def add(self, item):
        """Add a single item."""
        wm = self._with_removing_callback(item)
        if wm not in self.data:
            self.data.append(wm)
        
    def __iter__(self):
        """Iterate through the list."""
        with IterationGuard(self):
            for r in self.data:
                if r.valid:
                    yield r
                elif r not in self._pending: #pragma: no cover
                    self._pending.append(r)
        
    @remove_pending
    def discard(self, item):
        """Discard an item."""
        if item in self:
            self.remove(item)
    
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
            try:
                self.data.remove(self._pending.pop())
            except ValueError as e: #pragma: no cover
                pass
        
    def __len__(self):
        """Length of the callbacks."""
        return len(self.data) - len(self._pending)
        
    @remove_pending
    def prepend(self, item):
        """Insert an item into the beginning of the callback list."""
        wm = self._with_removing_callback(item)
        if wm in self.data:
            self.data.remove(wm)
        self.data.insert(0, wm)
        
    def __contains__(self, item):
        wm = WeakMethod(item)
        return wm in self.data
        
        