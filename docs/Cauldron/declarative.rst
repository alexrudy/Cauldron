.. currentmodule:: Cauldron.ext.declarative

Declarative Keywords
********************

This module, based on the `SQLAlchemy`_ `Declarative`_ extension, allows keywords to be configured as class attributes on custom classes.
These keywords can then be used as a class attribute which returns the keyword value, and when set, will trigger a keyword modify. Keyword
descriptors can also set event listeners for various Keyword methods, such as :meth:`~Cauldron.base.dispatcher.Keyword.check` and :meth:`~Cauldron.base.dispatcher.Keyword.preread`.

An example declarative class using keywords is below::

    from Cauldron.ext.declarative import KeywordDescriptor, DescriptorBase

    class Thing(DescriptorBase):

        enabled = KeywordDescriptor("THINGPOWER")

        @enabled.write
        def adjust_power(self, keyword, value):
            if bool(value):
                # TURN ON THE THING
                pass
            else:
                # TURN OFF THE THING
                pass
                
        @enabled.check
        def check_power(self, keyword, value):
            bool(value)
        


To use this declarative class, you must bind the class to a KTL Service object::

    from Cauldron import DFW
    svc = DFW.Service("THINGYSERVICE", conifg=None)
    Thing.set_service(svc)
    athingy = Thing()
    
    print(athingy.enabled)
    athingy.enabled = False


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
