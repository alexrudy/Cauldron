# -*- coding: utf-8 -*-
"""
A registry of setup and teardown functions for dispatchers and clients.
"""

import collections
import atexit
from .compat import WeakOrderedSet
from .utils.helpers import _inherited_docstring

__all__ = ['client', 'dispatcher', 'keys', 'teardown', 'Registry']

class Registry(object):
    """A registry of setup and teardown functions.
    
    This module contains two :class:`Registry` instances: ``client`` and ``dispatcher``.
    They serve as the setup and teardown registries for the KTL client and disptachetr
    side APIs. Additional setup or teardown functions can be registered using :meth:`setup_for`
    and :meth:`teardown_for`. The base keyword and service classes for a particular backend can
    be set using :meth:`keyword_for` and :meth:`service_for`. All of these methods are decorators
    and can be used as such in the appropriate places::
        
        from Cauldron import registry
        
        @regsitry.client.setup_for("mybackend")
        def mysetup():
            # Do some setup work here!
            pass
        
    
    """
    def __init__(self, name, doc=None, modname="Cauldron.DFW"):
        super(Registry, self).__init__()
        self.name = name
        self._setup = collections.defaultdict(WeakOrderedSet)
        self._teardown = collections.defaultdict(WeakOrderedSet)
        self._keyword = {}
        self._service = {}
        self._backends = set()
        self._backend = None
        self._modname = modname
        self._service_cls = None
        self._keyword_cls = None
        if doc is not None:
            self.__doc__ = doc
        atexit.register(self.teardown)
            
    @property
    def backend(self):
        """Get the backend name."""
        return self._backend
        
    def deferred(self, backend):
        """Register a backend as a deferred backend.
        
        Should only be used if the backend really will be set up by the time use() is called.
        """
        self._backends.add(backend)
        
    def keys(self):
        """Return the active and available registry keys."""
        return self._backends
        
    def guard(self, msg, error=RuntimeError):
        """Guard against backends that aren't set up."""
        if self._backend is None:
            raise error("The backend must be set before {0}. Call Cauldron.api.use('backend') to set the backend.".format(msg))
        
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
        self.guard("accessing the Keyword class")
        if self._keyword_cls is None:
            cls = self._keyword[self._backend]
            self._keyword_cls = type('Keyword', (cls, object),
                {'__module__':'{0}.Keyword'.format(self._modname)})
        return self._keyword_cls
        
    @property
    def Service(self):
        """The Service class."""
        self.guard("accessing the Service class")
        if self._service_cls is None:
            cls = self._service[self._backend]
            self._service_cls = type('Service', (cls, object),
                {'__module__':'{0}.Service'.format(self._modname)})
        return self._service_cls
        
    def keyword_for(self, backend, keyword=None):
        """Register a keyword class."""
        def _decorate(class_):
            if backend in self._keyword:
                raise KeyError("Cannot register multiple Keyword classes for backend '{0}'".format(backend))
            self._keyword[backend] = class_
            if backend in self._service:
                self._backends.add(backend)
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
            if backend in self._keyword:
                self._backends.add(backend)
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
        self.guard("calling the setup functions")
        for func in self._setup[self._backend]:
            func()
        for func in self._setup['all']:
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
        self._service_cls = None
        self._keyword_cls = None
        

client = Registry("client", doc="A registry of setup and teardown functions to support the KTL client interface.", modname="Cauldron.ktl")
dispatcher = Registry("dispatcher", doc="A registry of setup and teardown functions to support the KTL dispatcher interface.", modname="Cauldron.DFW")

def keys():
    """Keys available in both registries."""
    return list(set(client.keys()).union(dispatcher.keys()))

def teardown():
    """Teardown both the client and dispatcher."""
    client.teardown()
    dispatcher.teardown()