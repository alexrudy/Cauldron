.. module:: Cauldron

Cauldron - Abstraction layer for KTL
------------------------------------

Cauldron is a library to remove the dependency on the "Keck Telescope Libary", KTL.

KTL is a system used by UC Observatories for both Lick and Keck Observatories. It is primarily
a message passing system which behaves akin to a Keyword-Value store with distributed backends.

KTL uses come in two flavors: "Clients", which read and write to a KTL service, and "Dispatchers",
which maintain the truth value of keywords for a given service.

This library provides a python drop-in replacement for both clients and dispatchers which use the
KTL libraries and protocols. It is designed to seamlessly replace the need for KTL tools when
running on a local, non-production machine.

.. toctree::
    :maxdepth: 2
    
    ktl
    api
    base
    backends/index
    internals

Using Cauldron
==============

To use Cauldron, you must first select a backend via :func:`use`::
    
    import Cauldron
    Cauldron.use("local")
    

Then, where you would have imported a KTL library, you can call::
    
    from Cauldron import ktl
    

or for the python dispatcher framework::
    
    from Cauldron import DFW
    

To use the standard KTL implementation, use the "ktl" backend::
    
    import Cauldron
    Cauldron.use("ktl")
    
To use existing code which doesn't follow the ``from Cauldron import DFW``-style, you
can "install" the Cauldron modules into their default place on the system.::
    
    from Cauldron.api import install
    install()
    
You should do this before your code imports ``ktl`` or ``DFW``. This is a very hacky way
to install a module at runtime. Then again, most of Cauldron is a giant runtime hack, so your
mileage may vary.

Once you have done this, code which imports ``ktl`` or ``DFW`` will get the Cauldron versions, so
the following will work::
    
    import ktl, DFW
    


.. _REDIS: http://redis.io
