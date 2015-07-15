# -*- coding: utf-8 -*-
from __future__ import absolute_import

import weakref
from ...compat import WeakOrderedSet

class _DescriptorEvent(object):
    """Manage events attached to a keyword descriptor."""
    def __init__(self, name):
        super(_DescriptorEvent, self).__init__()
        self.name = name
        self.callbacks = WeakOrderedSet()
        self.listeners = weakref.WeakKeyDictionary()
        
    def listen(self, func):
        """Listen to a function."""
        self.callbacks.add(func)
        
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
        
class _KeywordListener(object):
    """A listener to help fire events on a keyword object."""
    def __init__(self, keyword, instance, event):
        super(_KeywordListener, self).__init__()
        self.event = weakref.ref(event)
        self.func = getattr(keyword, event.name)
        self.keyword = weakref.ref(keyword)
        self.instance = weakref.ref(instance)
        setattr(keyword, event.name, self)
        
    def __call__(self, *args, **kwargs):
        """Ensure that the dispatcher fires before the keyword's own implementation."""
        event = self.event()
        instance = self.instance()
        keyword = self.keyword()
        if keyword is None:
            raise RuntimeError("Keyword was garbage collected before event could fire.")
        if instance is not None:
            event.propagate(instance, keyword, *args, **kwargs)
        return self.func(*args, **kwargs)