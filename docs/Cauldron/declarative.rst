.. currentmodule:: Cauldron.ext.declarative

Declarative Keywords
********************

This module, based on the `SQLAlchemy`_ `Declarative`_ extension, allows keywords to be configured as class attributes on custom classes.
These keywords can then be used as a class attribute which returns the keyword value, and when set, will trigger a keyword modify. Keyword
descriptors can also set event listeners for various Keyword methods, such as :meth:`~Cauldron.base.dispatcher.Keyword.check` and :meth:`~Cauldron.base.dispatcher.Keyword.preread`.

An example declarative class using keywords is below::

    >>> from Cauldron.ext.declarative import KeywordDescriptor, DescriptorBase
    >>> class Thing(DescriptorBase):
    ...
    ...     enabled = KeywordDescriptor("THINGPOWER")
    ...
    ...     @enabled.write
    ...     def adjust_power(self, keyword, value):
    ...         if bool(value):
    ...             # TURN ON THE THING
    ...             pass
    ...         else:
    ...             # TURN OFF THE THING
    ...             pass
    ...
    ...     @enabled.check
    ...     def check_power(self, keyword, value):
    ...         bool(value)



To use this declarative class, you must bind the class to a KTL Service object::

    >>> from Cauldron import use
    >>> use("local")
    >>> from Cauldron import DFW
    >>> svc = DFW.Service("THINGYSERVICE", config=None)
    >>> Thing.bind(svc)
    >>> athingy = Thing()
    >>> athingy.enabled = True
    >>> athingy.enabled
    'True'


Events
======

The declarative interface provides events for several dispatcher keyword methods. These events recieve the same
arguments as their API counterparts, with the keyword instance itself passed as the first argument.

========== =========================================================================================================================
Event Name Keyword Method
========== =========================================================================================================================
callback   :meth:`~Cauldron.base.dispatcher.Keyword._propagate` (as if :meth:`~Cauldron.base.dispatcher.Keyword.callback` was used.)
preread    :meth:`~Cauldron.base.dispatcher.Keyword.preread`
read       :meth:`~Cauldron.base.dispatcher.Keyword.read`
postread   :meth:`~Cauldron.base.dispatcher.Keyword.postread`
prewrite   :meth:`~Cauldron.base.dispatcher.Keyword.prewrite`
write      :meth:`~Cauldron.base.dispatcher.Keyword.write`
postwrite  :meth:`~Cauldron.base.dispatcher.Keyword.postwrite`
check      :meth:`~Cauldron.base.dispatcher.Keyword.check`
========== =========================================================================================================================

Events are available by name on keyword descriptors. The events are callables which can be used as a decorator. They also have a :meth:`listen`
method which can be used to explicitly declare that a keyword listens for a function.

API/Reference
=============

.. automodapi:: Cauldron.ext.declarative.descriptor

.. _SQLAlchemy: http://www.sqlalchemy.org
.. _Declarative: http://docs.sqlalchemy.org/en/rel_1_0/orm/extensions/declarative/index.html
.. _descriptors: https://docs.python.org/2/howto/descriptor.html

Internals
=========

The Declarative extension deserves some additional explanation, as some of the design decisions may be opaque to the user or casual developer.

Descriptors
-----------

First, some notes about `descriptors`_. Descriptors are special python objects which implement a ``__get__`` method and optionally a ``__set__`` method. Importantly, instances of descriptors become class members of their parent class. This is required to ensure that attribute access is properly handled by the descriptor's ``__get__`` and ``__set__`` methods. As such, each descriptor instance cannot be associated with an individual parent instance. Rather, it must dynamically alter attributes depending on the parent instance that it receives to ``__get__`` or ``__set__``.

This is why `descriptors`_ know about their keyword name and value, but must be bound to a service and instance to connect events.

Binding
-------

Binding is the process by which we associate `descriptors`_ with instances of their parent class, and with specific KTL services. Binding is necessary because the descriptor must know the service it should call, but it must also know how to call instance methods on the parent instance. The first half of this problem is solved by service binding, and can happen at the class level. The second part of this problem is solved by instance binding, and must happen at the instance level.

Service Binding
^^^^^^^^^^^^^^^

Service binding associates a KTL service with an instance of a descriptor. This can be done either using the instance attribute on the descriptor, :attr:`KeywordDescriptor.service`, or the class method on the parent class, :meth:`DescriptorBase.bind`. When called on the parent class, :meth:`DescriptorBase.bind` simply sets :attr:`KeywordDescriptor.service` for each :class:`KeywordDescriptor` instance associated with that base class.
    
Instance Binding
^^^^^^^^^^^^^^^^

Instance binding associates a particular instance of a parent class (an instance of :class:`DescriptorBase`) with the descriptors on that class. Each instance of the parent class can be bound to the descriptors, and the binding can happen multiple times with no side effects. Binding allows the descriptor instance, which was created as a class variable on the parent class, to call bound methods of each instance. In the example at the beginning of this document, the method ``adjust_power`` is marked as listening for ``enabled.write``. Instance binding allows the keyword ``enabled`` to call ``adjust_power`` as a bound method, correctly filling in the ``self`` argument (along with the ``keyword`` and ``value`` arguments.) with an instance of the class ``Thing``.

Events
------

The concept of "binding" above explains how binding and descriptors work from the user's point of view. Internally, there is a little more complexity. This complexity allows events to trigger on theoretically any :class:`~Cauldron.base.dispatcher.Keyword` instance method, even if the Keyword class doesn't know about this extension.

This process works through three layers of "Event" classes. The top layer, ``_DescriptorEvent``, is what implements the decorator interface (``@``-syntax) in the example at the top of this document. The decorator interface registers each decorated function as a callback. Because most decorated functions are decorated at the time they are declared, they are decorated as regular functions (not even unbound methods). This means that the ``_DescriptorEvent`` cannot track which methods should be called while bound to the instance, and which ones should be called as regular functions. The ``_DescriptorEvent`` class is responsible for propagating event callbacks, but maintains no association with a specific parent instance.

The next layer is handled by the ``_KeywordEvent`` class. This class is used to wrap methods on :class:`~Cauldron.base.dispatcher.Keyword` instances. A single ``_KeywordEvent`` instance is used to wrap each instance method on :class:`~Cauldron.base.dispatcher.Keyword`. It intercepts method calls on :class:`~Cauldron.base.dispatcher.Keyword`. ``_KeywordEvent`` instances maintain a list of listeners. Listeners (``_KeywordListener``) associate an instance of the parent class, an instance of the descriptor, and an instance of the keyword together. They are weakly referenced, so that if any one of the constituent components (descriptor, parent instance, or keyword) is garbage collected, the listener will be removed.

.. automodapi:: Cauldron.ext.declarative.events
