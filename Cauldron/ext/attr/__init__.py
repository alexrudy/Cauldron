"""
Expose keywords as attributes on ktl services.
"""

def get_service(name):
    """Generate a service object for a given name."""
    from Cauldron.ktl.procedural import cached
    return cached(name)

class Service(object):
    """An attribute service"""
    
    _service = None
    # The KTL Service underlying this object.
    
    def __init__(self, name_or_service):
        super(Service, self).__init__()
        if isinstance(name_or_service, (str, bytes)):
            self._service = get_service(name_or_service)
        else:
            self._service = name_or_service
        
    def __getattr__(self, name):
        """Get an attribute."""
        if hasattr(self._service, name):
            return getattr(self._service, name)
        if name in self._service:
            keyword = self._service[name]
            if not keyword['monitored']:
                return keyword.read(binary=True)
            return keyword['binary']
        raise AttributeError(name)
        
    def __setattr__(self, name, value):
        """Set an attribute on this service object."""
        for obj in [self, self._service] + self._service.__class__.mro():
            if name in obj.__dict__:
                object.__setattr__(self, name, value)
                return
        if name in self._service:
            keyword = self._service[name]
            return keyword.write(value)
        raise AttributeError(name)