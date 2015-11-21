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

try:
    from DFW.Keyword import WrongDispatcher
except ImportError:
    class WrongDispatcher(ValueError):
        """Error raised for incorrect dispatchers in services."""
        pass

class CauldronException(Exception):
    """A base class to collect Cauldron Exceptions & Warnings."""
    pass

class CauldronWarning(CauldronException, RuntimeWarning):
    """A base class for all Cauldron warnings."""
    pass

class CauldronAPINotImplemented(CauldronException, NotImplementedError):
    """Exception raised when an API feature is not implemented."""
    pass
    
class ServiceNotStarted(CauldronException, KeyError):
    """Exception raised when starting a client which requires a dispatcher, and the dispatcher has not started."""
    pass

class CauldronAPINotImplementedWarning(CauldronWarning, CauldronAPINotImplemented):
    """Warning raised to indicate that an API feature is not implemented, and so was silently ignored."""
    pass
    
class CauldronXMLWarning(CauldronWarning):
    """Warning raised due to the non-strict use of XML in non-standard KTL backends."""
    pass
    

class DispatcherError(CauldronException):
    """Raised when something went wrong with the dispatcher."""
    pass
    
class ConfigurationMissing(CauldronWarning):
    """An exception raised when a configuration item is missing."""
    pass
    
