# -*- coding: utf-8 -*-

try:
    from six.moves.builtins import ReferenceError
except (NameError, ImportError): # pragma: no cover
    from weakref import ReferenceError

__all__ = ['ReferenceError']
