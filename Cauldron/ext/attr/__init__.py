"""
Expose keywords as attributes on ktl services.
"""

import contextlib

def get_service(name):
    """Generate a service object for a given name."""
    from Cauldron.ktl.procedural import cached
    if isinstance(name, (str, bytes)):
        return cached(name)
    return name
    
__all__ = ['Service', 'ktl_context']

@contextlib.contextmanager
def ktl_context(service, **kwargs):
    """A context in which various keyword values are set to the desired value.
    
    Use as follows::
        
        with ktl_context("saocon2", loop="open"):
            # Do some work here with loop = 'open'
            print("The loop is open!")
        
    This is equivalent, roughly, to::
        
        service = ktl.Service("saocon2")
        loop = service['loop'].read()
        try:
            service['loop'].write('open')
            # Do some work here with loop = 'open'
            print("The loop is open!")
        finally:
            service['loop'].write(loop)
    
    """
    service = get_service(service)
    initial_state = {}
    # Record the initial state.
    for keyword in kwargs:
        initial_state[keyword] = service[str(keyword)].read()
    try:
        for keyword, value in kwargs.items():
            service[str(keyword)].write(value)
        yield
    finally:
        for keyword, value in initial_state.items():
            service[str(keyword)].write(value)

class Service(object):
    """A ktl Service like object with keywords exposed via
    attributes. This gives less precise control over the use
    of keywords, but allows for more concise scripts::
        
        svc = Service("testsvc")
        svc.mykeyword = "hello"
        svc.mykeyword
        "hello"
    
    """
    
    _service = None
    # The KTL Service underlying this object.
    
    def __init__(self, name_or_service):
        super(Service, self).__init__()
        self._service = get_service(name_or_service)
        
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
        if name == "_service":
            object.__setattr__(self, name, value)
        for obj in [self, self._service] + self._service.__class__.mro():
            if name in obj.__dict__:
                object.__setattr__(self, name, value)
                return
        if name in self._service:
            keyword = self._service[name]
            return keyword.write(value)
        raise AttributeError(name)