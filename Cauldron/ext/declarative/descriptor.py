# -*- coding: utf-8 -*-
"""
Implement the declarative descriptor.
"""
from __future__ import absolute_import

import weakref
from .events import _DescriptorEvent, _KeywordEvent
from .utils import descriptor__get__, hybridmethod
from ...exc import CauldronException

__all__ = ['KeywordDescriptor', 'DescriptorBase', 'ServiceNotBound']

class ServiceNotBound(CauldronException):
    """Error raised when a service is not bound to a descriptor."""
    pass

class IntegrityError(CauldronException):
    """Raised to indicate an instance has a differing initial value from the one in the keyword store."""
    pass

class DescriptorBase(object):
    """A keyword descriptor base class which assists in binding descriptors to keywords.
    
    This class should be used as a base class for any class that will use :class:`KeywordDescriptor` to
    describe :mod:`Cauldron` keywords as attributes.
    
    This class provides a :meth:`bind` method to associate a :mod:`Cauldron` Service with the descriptors
    on this class. There are two stages to binding:
    
    1. Set the DFW Service for these keywords via :meth:`bind`. This can be done at the class level.
    2. Bind an instance to the the service. This can be done at __init__ time.
    
    """
    
    def __init__(self, *args, **kwargs):
        """This inializer tries to bind the instance, if it can."""
        super(DescriptorBase, self).__init__(*args, **kwargs)
        try:
            self.bind()
        except ServiceNotBound as e:
            # We swallow this exception, because the instance may not be
            # bound to a service.
            pass
    
    @classmethod
    def keyword_descriptors(cls):
        """Iterate over the keyword descriptors which are members of this class."""
        for var in dir(cls):
            try:
                member = getattr(cls, var)
                if isinstance(member, KeywordDescriptor):
                    yield member
            except Exception:
                # We don't know what happened here, but there are lots of ways
                # to override class-level attribute access and screw this up.
                pass
    
    @hybridmethod
    def bind(self, service=None):
        """Bind a service to the descriptors in this class.
        
        This method can be called either on the class or the instance. On the class,
        it associates a particular Cauldron KTL Service with the the keywords which
        are attached to this class. For an instance, it associates the Cauldron KTL
        Service if provided, and links the callback methods appropriately.
        
        :param service: The KTL Cauldron Service, or None, to bind to the keywords
            attached to this object.
        :raises: :exc:`ServiceNotBound` if there is no KTL Cauldron Service associated
            with this instance.
        """
        try:
            for desc in self.keyword_descriptors():
                desc.bind(self, service)
        except ServiceNotBound:
            raise ServiceNotBound("In order to bind this object's keyword descriptors, "
            "you must set the appropriate service via the bind(service=...) method.")
            
    @bind.classmethod
    def bind(cls, service=None):
        """Classmethod implementation of bind. See :meth:`bind` above."""
        if service is None:
            raise ServiceNotBound("In order to bind this object's keyword descriptors, "
            "you must set the appropriate service via the bind(service=...) method.")
        for desc in cls.keyword_descriptors():
            desc.service = service

class KeywordDescriptor(object):
    """A descriptor which maintains a relationship with a keyword.
    
    The descriptor should be used as a class level variable. It can be accessed as
    a regular instance variable, where it will return the result of :meth:`Keyword.update`
    operations. Setting the instance variable will result in a :meth:`Keyword.modify` operation.
    
    Parameters
    ----------
    name : str
        Keyword name. Case-insensitive, will be translated to upper case.
    
    initial : str
        Keyword initial value, should be a string. If not set, no initial value is used
        and the descriptor will return ``None`` before the keyword is bound.
    
    type : function
        A function which converts an inbound value to the appropraite python type. The python type
        returned by this function should be suitable for use as a string to modify the keyword.
        
    doc : str
        The docstring for this keyword descriptor.
    
    readonly : bool
        Set this keyword descriptor to be read-only.
        
    writeonly : bool
        Set this keyword descriptor to be write-only.
    
    """
    
    _EVENTS = ['preread', 'read', 'postread', 'prewrite', 'write', 'postwrite', 'check']
    _service = None
    
    def __init__(self, name, initial=None, type=lambda v : v, doc=None, readonly=False, writeonly=False):
        super(KeywordDescriptor, self).__init__()
        self.name = name.upper()
        self.type = type
        self.__doc__ = doc
        if readonly and writeonly:
            raise ValueError("Keyword {0} cannot be 'readonly' and 'writeonly'.".format(self.name))
        self.readonly = readonly
        self.writeonly = writeonly
        
        # Prepare the events interface.
        self._events = []
        for event in self._EVENTS:
            evt = _DescriptorEvent(event)
            setattr(self, event, evt)
            self._events.append(evt)
            
        # We handle 'callback' separately, as it triggers on the keyword's _propogate method.
        #TODO: We should check that this works with DFW and ktl builtins, its kind of a hack
        # here
        self.callback = _DescriptorEvent("_propogate")
        self._events.append(self.callback)
        
        self._attr = "_{0}_{1}".format(self.__class__.__name__, self.name)
        self._initial = initial
        self._real_initial = initial
        self._events.append(self.callback)
        
    def __repr__(self):
        """Represent"""
        try:
            repr_bind = " bound to {0}".format(self.service) if self.service is not None else ""
        except weakref.ReferenceError:
            repr_bind = ""
        
        return "<{0} name={1}{2}>".format(self.__class__.__name__, self.name, repr_bind)
        
    @descriptor__get__
    def __get__(self, obj, objtype=None):
        """Getter"""
        if self.writeonly:
            raise ValueError("Keyword {0} is write-only.".format(self.name))
        try:
            return self.type(self.keyword.update())
        except ServiceNotBound:
            return self.type(getattr(obj, self._attr, self._initial))
        
    def __set__(self, obj, value):
        """Set the value."""
        if self.readonly:
            raise ValueError("Keyword {0} is read-only.".format(self.name))
        try:
            return self.keyword.modify(str(self.type(value)))
        except ServiceNotBound:
            return setattr(obj, self._attr, self.type(value))
        
    def bind(self, obj, service=None):
        """Bind a service to this descriptor, and the descriptor to an instance.
        
        Binding an instance of :class:`DescriptorBase` to this descriptor activates
        the listening of events attached to the underlying keyword object.
        
        Binding an instance of :class:`DescriptorBase` to this descriptor will cause
        the descriptor to resolve the initial value of the keyword. This initial value
        will be taken from the instance itself, if the descriptor was modified before
        it was bound to this instnace, or the initial value as set by this descriptor
        will be used. When the initial value conflicts with a value already written
        to the underlying keyword, :exc:`IntegrityError` will be raised.
        
        If this descriptor has already been bound to any one instance, the descriptor
        level initial value will not be used, and instead only an instance-level initial
        value may be used.
        
        Parameters
        ----------
        obj : object
            The python instance which owns this descriptor. This is used to bind
            instance method callbacks to changes in this descriptor's value.
        
        service : :class:`DFW.Service.Service`
            The DFW Service to be used for this descriptor. May also be set via the
            :attr:`service` attribute.
        
        """
        if service is not None:
            self.service = service
        
        # We do this here to retain a reference to the same keyword object
        # thoughout the course of this function.
        keyword = self.keyword
        
        # Compute the initial value.
        try:
            initial = str(self.type(getattr(obj, self._attr, self._initial)))
        except TypeError:
            # We catch this error in case it was caused because no initial value was set.
            # If an initial value was set, then we want to raise this back to the user.
            if not (self._initial is None and not hasattr(obj, self._attr)):
                raise
        else:
            if getattr(obj, self._attr, self._initial) is None:
                # Do nothing if it was really None everywhere.
                pass
            elif keyword['value'] is None:
                # Only modify the keyword value if it wasn't already set to anything.
                keyword.modify(initial)
            elif keyword['value'] == initial:
                # But ignore the case where the current keyword value already matches the initial value
                pass
            else:
                raise IntegrityError("Keyword {0!r} has a value {1!r}, and descriptor has initial value {2!r} which do not match.".format(keyword, keyword['value'], initial))
            
            # Once we've bound an initial value, we set it to None
            # so that the descriptor-level initial value can't be invoked multiple times.
            self._initial = None
            # The original value is still available via ._real_initial, if it is required.
        
        # Clean up the instance initial values.
        try:
            delattr(obj, self._attr)
        except AttributeError:
            pass
        
        
        for event in self._events:
            _KeywordEvent(self.keyword, obj, event)
        
    @property
    def service(self):
        """The DFW Service associated with this descriptor."""
        return self._service
    
    @service.setter
    def service(self, value):
        """Set the service via a weakreference proxy."""
        self._service = weakref.proxy(value)
        
    @property
    def keyword(self):
        """The keyword instance for this descriptor."""
        try:
            return self._service[self.name]
        except (AttributeError, TypeError, weakref.ReferenceError):
            raise ServiceNotBound("No service is bound to {0}".format(self))
        

    