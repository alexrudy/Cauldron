.. module:: Cauldron.base

Cauldron KTL API
****************

The Cauldron KTL API mimics the real KTL API for clients and DFW API for server-side components. A brief introduction to using each component is below.

Using a Cauldron KTL Client
===========================

To use a client, you must first select a backend via :func:`use`::

    import Cauldron
    Cauldron.use("mock")


In this example, we use the "mock" backend, as it doesn't require a dispatcher to be running. All dispatchers will be filled in with caching dispatchers at runtime.

Then, import the ktl library and create a service clinet::

    from Cauldron import ktl
    service = ktl.Service("MYSERVICENAME")


To access a keyword, you can index the service object like a dictionary::

    keyword = service["AKEYWORD"]
    keyword.write("some value")
    value = keyword.read()


Using a Cauldron DFW dispatcher
===============================

Dispatchers are little more tricky in real-world use, as they respond to arbitrary requests from ktl clients. In the simplest implementation, you only need a dispatcher (instance of :class:`~Cauldron.DFW.Service`), from which you can access keyword objects, and attach callbacks to them. For example::

    import Cauldron, sys
    Cauldron.use("mock")
    from Cauldron import DFW
    service = DFW.Service("MYSERVICENAME", config=None)
    keyword = service["AKEYWORD"]
    keyword.callback(lambda kwd : sys.stdout.write("Hello\n"))


A more sophisticated (and correct) use of a dispatcher is to provide custom implementation for keywords which can validate keyword values as they are written, and which can respond with proper values as they are read. Imagine that you have a hardware widget with two functions and you wish to expose the widget via the keyword system::

    def get_widget_value():
        return 5

    def set_widget_value(value):
        print("Widget set to {0}".format(value))

Lets pretend that the widget only accepts integer values, and that negative numbers will cause an error for the widget. We can implement a custom keyword class for this widget using the following::

    from Cauldron.types import DispatcherKeywordType

    class WidgetKeyword(DispatcherKeywordType):

        def __init__(self, service):
            super(WidgetKeyword, self).__init__(service=service, name="MYWIDGET", initial=5)

        def read(self):
            return get_widget_value()

        def write(self, value):
            value = int(value)
            if value < 0:
                raise ValueError("Widget can't be less than zero.")
            set_widget_value(value)
            return str(value)



Now we'd normally set up the keyword during the service's setup function (see :class:`~Cauldron.DFW.Service`)::

    def setup(service):
        WidgetKeyword(service)

    service = DFW.Service("WIDGETSERVICE", setup=setup, config=None)


Dispatchers are asynchronous, but keywords are internally synchronized. This means that multiple keywords can be modified simultaneously, but an individual keyword can only be modified by one thread at a time. Note that callbacks can be asynchronously called, and so they shouldn't depend on the state of a keyword at a given time.

Subclassing :class:`~Cauldron.DFW.Keyword`
------------------------------------------

As shown above, a common pattern for writing KTL dispatchers is to subclass the keyword type to provide specific responses. Keywords have several methods which impact their operation.


API Implementation Status
=========================

A brief summary of major KTL API features is provided in the table below. API features marked as *Planned* are ones that I do intend to implement at some point in support of ShadyAO. API features marked as *Not Implemented* would require more work.

======================== =================== ========
Feature                  Status              Comments
======================== =================== ========
Synchronous read/write   Implemented
Asynchronous read/write  Implemented         KTL calls are still serial on local backends.
Heartbeats               *Implemented*       Support for periods implemented.
Callbacks                Implemented
Polling                  Not Implemented
Scheduling               Implemented
Expressions              Not Implemented
XML Keyword Validation   Implemented
Operator Overloading     Not Implemented
======================== =================== ========

When Cauldron does not implement a feature, using that feature will raise an :exc:`~Cauldron.exc.CauldronAPINotImplemented` error, which is a subclass of :exc:`NotImplementedError`.

ktl Reference/API
=================

.. automodapi:: Cauldron.ktl
    :skip: Service, Keyword

.. automodapi:: Cauldron.ktl.Keyword

.. automodapi:: Cauldron.ktl.Service

.. automodapi:: Cauldron.ktl.procedural

DFW Reference/API
=================

.. automodapi:: Cauldron.DFW
    :skip: Service

.. automodapi:: Cauldron.DFW.Service

.. automodapi:: Cauldron.DFW.Keyword
