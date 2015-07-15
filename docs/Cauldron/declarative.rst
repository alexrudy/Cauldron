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

        @enabled.callback
        def adjust_power(self, keyword):
            if keyword['value']:
                # TURN ON THE THING
                pass
            else:
                # TURN OFF THE THING
                pass



To use this declarative class, you must bind an instance of it to a service object::

    from Cauldron import DFW
    athingy = Thing()
    svc = DFW.Service("THINGYSERVICE", conifg=None)
    athingy.bind(svc)

    print(athingy.enabled)
    athingy.enabled = False


Events
======

The declarative interface provides events for 

API/Reference
=============

.. automodapi:: Cauldron.ext.declarative.descriptor

.. _SQLAlchemy: http://www.sqlalchemy.org
.. _Declarative: http://docs.sqlalchemy.org/en/rel_1_0/orm/extensions/declarative/index.html
