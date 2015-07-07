.. module:: Cauldron

************************************
Cauldron - Abstraction layer for KTL
************************************

Cauldron is a KTL Compatibility Layer.

It is designed to expose the KTL API and to mimic KTL python modules without using the KTL backend. In order to expose the KTL-like backend, there is an abstract base class which is designed to mimics the API for KTL keywords and services. There are two specific backends implemented to the KTL interface, :mod:`Cauldron.local`, a process-local keyword interface, and :mod:`Cauldron.redis`, a REDIS_ based backend.

To use :mod:`Cauldron`, you will need to select a backend, e.g. the "local" or "redis" backend::
    
    >>> import Cauldron
    >>> Cauldron.use("local")
    

Once you have selected a backend, you can replace calls to :mod:`ktl` with the following::
    
    from Cauldron import ktl
    

Or for dispatchers::
    
    from Cauldron import DFW
    

To use the true KTL backend, call::
    
    import Cauldron
    Cauldron.use("ktl")


.. toctree::
    :maxdepth: 1
    
    api
    local
    redis
    

.. _REDIS: http://redis.io