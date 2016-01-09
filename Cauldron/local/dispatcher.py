# -*- coding: utf-8 -*-
"""
Local dispatcher.

The local interface is process-local. It is lightweight, and good for testing environments, but doesn't handle anything that wouldn't normally be process local.

"""

from ..base import DispatcherService, DispatcherKeyword
from ..utils.callbacks import Callbacks
from .. import registry
from ..exc import WrongDispatcher

import weakref
import os

__all__ = ['Service', 'Keyword']

_registry = weakref.WeakValueDictionary()

@registry.dispatcher.teardown_for("local")
def clear():
    """Clear the registry."""
    _registry.clear()

@registry.dispatcher.service_for("local")
class Service(DispatcherService):
    
    def _save_cache(self, location):
        """Cache this service to disk."""
        try:
            import yaml
        except ImportError:
            self.log.debug("Caching disabled, YAML is not installed.")
            return
        
        filename = os.path.join(location, "{0}.yml".format(self._fqn))
        data = {
            'service' : self.name,
            'config' : self._configuration_location,
            'xml' : self.xml is not None,
            'keywords' : {}
        }
        for keyword in self:
            if keyword is not None:
                data['keywords'][keyword.name] = {
                    'value' : keyword.value,
                    'type' : keyword.KTL_TYPE,
                }
        with open(filename, 'w') as f:
            yaml.dump(data, f)
            
    def _load_cache(self, location):
        """Load this service from a cache location."""
        try:
            import yaml
        except ImportError:
            self.log.debug("Caching disabled, YAML is not installed.")
            return
        
        from Cauldron import DFW
        filename = os.path.join(location, "{0}.yml".format(self._fqn))
        try:
            with open(filename, 'r') as f:
                data = yaml.load(f)
        except IOError:
            self.log.debug("Cache did not exist.")
            return
            
        for keyword, properties in data['keywords'].items():
            try:
                if keyword not in self:
                    cls = DFW.Keyword.types[properties['type']]
                    kwd = cls(keyword, service=self)
                    kwd.value = properties['value']
                else:
                    self[keyword].value = properties['value']
            except WrongDispatcher as e:
                pass
    
    @classmethod
    def get_service(cls, name):
        """Get a dispatcher for a service."""
        #TODO: Support inverse client startup ordering.
        name = str(name).lower()
        return _registry[name]
    
    def __init__(self, name, config, setup=None, dispatcher=None):
        if str(name).lower() in _registry:
            raise ValueError("Cannot have two services with name '{0}' in local registry.".format(name))
        super(Service, self).__init__(name, config, setup, dispatcher)
        
    def _prepare(self):
        """Prepare for operation."""
        cachedir = self._config.get('local', 'cache')
        if os.path.exists(cachedir):
            self._load_cache(cachedir)
        else:
            os.makedirs(cachedir)
        self._cache_location = cachedir
        
    def _begin(self):
        """Indicate that this service is ready to act, by inserting it into the local registry."""
        _registry[self.name] = self
        self._save_cache(self._config.get('local', 'cache'))
        
    def shutdown(self):
        """To shutdown this service, delete it."""
        self._save_cache(self._config.get('local', 'cache'))

@registry.dispatcher.keyword_for("local")
class Keyword(DispatcherKeyword):
    
    def __init__(self, name, service, initial=None, period=None):
        super(Keyword, self).__init__(name, service, initial, period)
        self._consumers = Callbacks()
    
    def _broadcast(self, value):
        """Notify consumers that this value has changed."""
        self._consumers(value)
        
