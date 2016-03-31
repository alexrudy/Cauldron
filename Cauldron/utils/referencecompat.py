# -*- coding: utf-8 -*-

try:
    from six.moves.builtins import ReferenceError
except (NameError, ImportError):
    from weakref import ReferenceError

__all__ = ['ReferenceError']
