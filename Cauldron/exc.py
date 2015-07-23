# -*- coding: utf-8 -*-
"""
Exceptions and warnings.
"""

__all__ = ['NoWriteNecessary', 'CauldronWarning', 'CauldronException', 'CauldronAPINotImplemented', 'ServiceNotStarted']

try:
    from DFW.Keyword import NoWriteNecessary
except ImportError:
    class NoWriteNecessary(Exception):
        """Raised to cancel a keyword write in progress."""
        pass

class CauldronWarning(RuntimeWarning):
    pass
    
class CauldronException(Exception):
    pass
    
class CauldronAPINotImplemented(CauldronException, NotImplementedError):
    pass
    
class CauldronAPINotImplementedWarning(CauldronWarning):
    pass
    
class ServiceNotStarted(CauldronException, KeyError):
    """Exception raised when starting a client which requires a dispatcher, and the dispatcher has not started."""
    pass