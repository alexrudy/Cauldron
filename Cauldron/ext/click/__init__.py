# -*- coding: utf-8 -*-

try:
    import click
except ImportError:
    raise ImportError("Cauldron.ext.click requires the click package.")

from ...api import use

__all__ = ['backend', 'service']

def select_backend(ctx, param, value):
    """Callback to set the Cauldron backend."""
    if not value or ctx.resilient_parsing:
        return
    use(str(value))

def backend(default=None):
    """Click options to set up a Cauldron backend."""
    option = click.option("-k", "--backend", expose_value=False, is_eager=True, 
                 callback=select_backend, help="Set the Cauldron backend.", 
                 default=default)
    def decorate(func):
        return option(func)
    
    return decorate

backend_option = backend

def construct_service(ctx, param, value):
    """Construct a service."""
    if not value:
        return
    from Cauldron import ktl
    return ktl.Service(str(value))

def service(default=None, backend=True):
    """Add a service argument which returns a ktl.Service class."""
    option = click.option("-s", "--service", callback=construct_service,
                          help="KTL Service name to use.", default=default)
    
    backend_default = None
    if backend and isinstance(backend, str):
        backend_default = backend
    
    def decorate(func):
        if backend:
            func = backend_option(default=backend_default)(func)
        return option(func)
        