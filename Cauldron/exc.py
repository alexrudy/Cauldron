# -*- coding: utf-8 -*-
"""
Exceptions and warnings.
"""

__all__ = ['NoWriteNecessary', 'CauldronWarning', 'CauldronException', 'CauldronAPINotImplemented']

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