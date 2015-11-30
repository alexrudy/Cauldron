.. module:: Cauldron

Cauldron - Abstraction layer for KTL
------------------------------------

Cauldron is a library to remove the dependency on the :ref:`ktl`, :ref:`KTL <ktl>`.

:ref:`KTL <ktl>` is a system used by UC Observatories for both Lick and Keck Observatories. It is primarily
a message passing system which behaves akin to a Keyword-Value store with distributed backends.

:ref:`KTL <ktl>` uses come in two flavors: "Clients", which read and write to a :ref:`KTL <ktl>` service, and "Dispatchers",
which maintain the truth value of keywords for a given service.

This library provides a python drop-in replacement for both clients and dispatchers which use the
:ref:`KTL <ktl>` libraries and protocols. It is designed to seamlessly replace the need for :ref:`KTL <ktl>` tools when
running on a local, non-production machine.

.. toctree::
    :maxdepth: 2
    
    ktl
    api
    base
    configuration
    xml
    declarative
    backends/index
    internals

Installation
============

Cauldron is a standard python package which uses :mod:`setuptools`. It uses the :mod:`astropy` :mod:`setuptools`
which fix some bugs and provide some nice documentation advantages. This does mean that :mod:`Cauldron`
depends on :mod:`astropy`, though this is an installation and test dependency, not a runtime dependency.

Cauldron also depends on the :mod:`six` module. Some Cauldron backends depend on other third party modules.
To install all third party modules, you can use ``pip``::
    
    $ pip install -r requirements.txt
    

To install Cauldron, use pip::
    
    $ pip install git+https://github.com/alexrudy/Cauldron
    

Using Cauldron
==============

To use Cauldron, you must first select a backend via :func:`use`::
    
    import Cauldron
    Cauldron.use("local")
    

Then, where you would have imported a :ref:`KTL <ktl>` library, you can call::
    
    from Cauldron import ktl
    

or for the python dispatcher framework::
    
    from Cauldron import DFW
    

To use the standard :ref:`KTL <ktl>` implementation, use the "ktl" backend::
    
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
