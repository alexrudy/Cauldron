# -*- coding: utf-8 -*-

import abc
import textwrap
import re
import inspect
from ..exc import CauldronAPINotImplemented, CauldronAPINotImplementedWarning

try:
    from astropy.utils.decorators import wraps
except ImportError:
    from functools import wraps

__all__ = ['api_not_implemented', 'api_not_required', 'api_required']

def _inherited_docstring(*clses):
    """Make a class inherit docstrings."""
    for cls in clses:
        for bcls in inspect.getmro(cls):
            if ('__doc__' in bcls.__dict__ and 
                bcls.__dict__['__doc__'] is not None and 
                bcls.__dict__['__doc__'].strip() != ''):
                return bcls.__dict__['__doc__']
    else:
        raise ValueError("Can't find an inheritable docstring for {0!r}".format(cls))

def _docstring_left_indent(docstring):
    """Compute the left indent from a docstring."""
    lines = docstring.expandtabs().splitlines()
    if len(lines) > 1:
        matches = [ re.search('(\S)', line) for line in lines[1:] ]
        try:
            left_indent = min(match.start() for match in matches if match)
        except ValueError:
            left_indent = 0
    else:
        left_indent = 0
    return left_indent

def _append_to_docstring(docstring, text):
    """Append `text` to `docstring` preserving indentation rules."""
    left_indent = _docstring_left_indent(docstring)
    newlines = [''] + text.splitlines()
    newlines = [ (' ' * left_indent) + newline for newline in newlines ]
    docstring += "\n" + "\n".join(newlines)
    return docstring
    
def _prepend_to_docstring(docstring, text):
    """Prepend `text` to `docstring` preserving indentation rules."""
    left_indent = _docstring_left_indent(docstring) * ' '
    newlines = [''] + text.splitlines()
    newlines = [ left_indent + newline for newline in newlines ]
    docstring = "\n" + "\n".join(newlines) + ("\n" + left_indent) * 2  + docstring
    return docstring
    

def api_not_implemented(func):
    """A decorator to correctly set the API not implemented."""
    
    func.__doc__ = _append_to_docstring(func.__doc__, textwrap.dedent("""
    .. warning:: `{0}` is not implemented in the Cauldron version of the KTL API.
    """.format(func.__name__)))
    
    @wraps(func)
    def api_not_implemented(*args, **kwargs):
        """Sub-function to handle API not implmeneted."""
        raise CauldronAPINotImplemented("The Cauldron API does not support '{0}'.".format(func.__name__))
    
    return api_not_implemented
    
def api_not_required(func):
    """A decorator to mark a function as implementing a not-required API"""
    
    func.__doc__ = _append_to_docstring(func.__doc__, textwrap.dedent("""
    
    .. note:: Cauldron backends are not required to implement this function. If the do not, it will raise an :exc:`CauldronAPINotImplemented` error.
    
    """))
    
    @wraps(func)
    def api_not_required(*args, **kwargs):
        """Sub-function to handle API not implmeneted."""
        raise CauldronAPINotImplemented("The Cauldron API does require support of '{0}'.".format(func.__name__))
    
    return api_not_required
    
def api_required(func):
    """A decorator to mark a function as abstract and requiring a backend implementation."""
    
    func.__doc__ = _append_to_docstring(func.__doc__, textwrap.dedent("""
    
    *This is an abstract method. Backends must implement this method*
    
    """))
    
    return abc.abstractmethod(func)
    
def api_override(func):
    """A decorator to mark a function as something subclasses can override."""
    func.__doc__ = _append_to_docstring(func.__doc__, textwrap.dedent("""
    
    *This method can be overridden to provide specific behavior in user subclasses.*
    
    """))
    
    return func
    
class _Setting(object):
    """A settings object, which can be passed around by value."""
    def __init__(self, name, value, lock=None):
        super(_Setting, self).__init__()
        self.name = name
        self.__value = value
        self._lock = lock
    
    @property
    def value(self):
        """Setting's boolean value"""
        return self.__value
        
    @value.setter
    def value(self, new_value):
        """Set the new value."""
        if self._lock is not None and self._lock:
            raise RuntimeError("Setting '{0}' is locked by '{1}', can't change value.".format(self.name, self._lock.name))
        self.__value = bool(new_value)
        
    @property
    def inverse(self):
        """A setting which is always the inverse of this setting."""
        return _SettingInverse(self)
        
    def __invert__(self):
        """Handle inversion."""
        return _SettingInverse(self)
    
    def __repr__(self):
        """Represent this value"""
        return "<Setting {0}={1}>".format(self.name, self.value)
    
    def __bool__(self):
        """Cast this setting to it's own boolean value."""
        return bool(self.value)
        
    def __nonzero__(self):
        """Cast setting to a boolean value (Python 2)"""
        return self.__bool__()
        
    def on(self):
        """Turn this setting on."""
        self.value = True
    
    def off(self):
        """Turn this setting off."""
        self.value = False
        
class _SettingInverse(_Setting):
    """The inverse of a setting object."""
    def __init__(self, setting):
        self.__setting = setting
        super(_SettingInverse, self).__init__(name = "~{0}".format(setting.name), value = not setting, lock=setting._lock)
        
    @property
    def value(self):
        """Get this setting's value."""
        return not self.__setting.value
    
    @value.setter
    def value(self, new_value):
        """Set this setting's value."""
        self.__setting.value = not new_value

        