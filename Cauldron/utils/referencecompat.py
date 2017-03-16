# -*- coding: utf-8 -*-
import sys
try:
    if sys.version_info[0] < 3:
        from __builtins__ import ReferenceError
    else:
        from builtins import ReferenceError
except (NameError, ImportError): # pragma: no cover
    from weakref import ReferenceError

__all__ = ['ReferenceError']
