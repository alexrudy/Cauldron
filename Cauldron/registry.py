# -*- coding: utf-8 -*-
"""
A registry of setup and teardown functions for dispatchers and clients.
"""

import collections
from .compat import WeakOrderedSet

__all__ = ['client', 'dispatcher', 'keys']

class _Registry(object):
    """A registry of setup and teardown functions."""
    def __init__(self):
        super(_Registry, self).__init__()
        self._setup = collections.defaultdict(WeakOrderedSet)
        self._teardown = collections.defaultdict(WeakOrderedSet)
        self._keyword = {}
        self._service = {}
        self._backend = None
        
    def keys(self):
        """Return the active and available registry keys."""
        return list(set(self._keyword.keys()).union(self._service.keys()))
        
    def _guard(self, msg):
        """Guard against backends that aren't set up."""
        if self._backend is None:
            raise RuntimeError("The backend must be set before {0}. Call Cauldron.use('backend') to set the backend.".format(msg))
        
    def _insert_setup(self, func, backend='all'):
        """Add a setup function for a particual backend."""
        self._setup[backend].add(func)
        
    def _insert_teardown(self, func, backend='all'):
        """Insert a teardown."""
        self._teardown[backend].add(func)
        
    def use(self, backend):
        """Set the backend."""
        if self._backend is not None:
            raise RuntimeError("The backend cannot be set twice. It is already '{0}'.".format(self._backend))
        self._backend = backend
    
    @property
    def Keyword(self):
        """The Keyword class."""
        self._guard("accessing the Keyword class")
        return self._keyword[self._backend]
        
    @property
    def Service(self):
        """The Service class."""
        self._guard("accessing the Service class")
        return self._service[self._backend]
        
    def keyword_for(self, backend, keyword=None):
        """Register a keyword class."""
        def _decorate(class_):
            if backend in self._keyword:
                raise KeyError("Cannot register multiple Keyword classes for backend '{0}'".format(backend))
            self._keyword[backend] = class_
            return class_
        if keyword is None:
            return _decorate
        return _decorate(keyword)
        
    def service_for(self, backend, service=None):
        """Register a service"""
        def _decorate(class_):
            if backend in self._service:
                raise KeyError("Cannot register multiple Service classes for backend '{0}'".format(backend))
            self._service[backend] = class_
            return class_
        if service is None:
            return _decorate
        return _decorate(service)
    
    def setup_for(self, backend):
        """Register a setup function."""
        def _decorate(func):
            self._insert_setup(func, backend)
            return func
        if callable(backend):
            self._insert_setup(backend, 'all')
            return backend
        return _decorate
    
    def teardown_for(self, backend):
        """Register a teardown function."""
        def _decorate(func):
            self._insert_teardown(func, backend)
            return func
        if callable(backend):
            self._insert_teardown(backend, 'all')
            return backend
        return _decorate
        
    def setup(self):
        """Do the setup process."""
        self._guard("calling the setup functions")
        for func in self._setup['all']:
            func()
        for func in self._setup[self._backend]:
            func()
    
    def teardown(self):
        """Do the teardown process."""
        for func in self._teardown['all']:
            func()
        if self._backend is None:
            return
        for func in self._teardown[self._backend]:
            func()
        self._backend = None
        

client = _Registry()
dispatcher = _Registry()

def keys():
    """Keys available in both registries."""
    return list(set(client.keys()).union(dispatcher.keys()))

def teardown():
    """Teardown both the client and dispatcher."""
    client.teardown()
    dispatcher.teardown()