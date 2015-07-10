# -*- coding: utf-8 -*-

import functools
import abc
import textwrap
from ..exc import CauldronAPINotImplemented, CauldronAPINotImplementedWarning

__all__ = ['api_not_implemented', 'api_not_required', 'api_required']

def api_not_implemented(func):
    """A decorator to correctly set the API not implemented."""
    
    func.__doc__ += "\n\n" + textwrap.dedent("""
    .. warning:: {0} is not implemented in the Cauldron version of the KTL API.
    """.format(func.__name__))
    
    @functools.wraps(func)
    def api_not_implemented(*args, **kwargs):
        """Sub-function to handle API not implmeneted."""
        raise CauldronAPINotImplemented("The Cauldron API does not support '{0}'.".format(func.__name__))
    
    return api_not_implemented
    
def api_not_required(func):
    """A decorator to mark a function as implementing a not-required API"""
    
    func.__doc__ += textwrap.dedent("""
    
    .. note:: Cauldron backends are not required to implement this function. If the do not, it will raise an :exc:`CauldronAPINotImplemented` error.
    
    """)
    
    return func
    
def api_required(func):
    """A decorator to mark a function as abstract and requiring a backend implementation."""
    
    func.__doc__ += textwrap.dedent("""
    
    *This is an abstract method. Backends must implement this method*
    
    """)
    
    return abc.abstractmethod(func)
    
def api_override(func):
    """A decorator to mark a function as something subclasses can override."""
    func.__doc__ += textwrap.dedent("""
    
    *This method can be overridden to provide specific behavior in user subclasses.*
    
    """)
    
    return func