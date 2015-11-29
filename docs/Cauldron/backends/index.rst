.. _backends:

Cauldron Backends
*****************

Cauldron has a few backends implemented, and it is easy to implement additional backends.

.. toctree::
    :maxdepth: 2
    
    local
    redis
    zmq

Implementing a Backend
----------------------

Implementing a new KTL backend requires a client and dispatcher implementation of both Keyword and Service. Provide subclasses of :class:`ClientKeyword`, :class:`ClientService`, :class:`DispatcherKeyword` and :class:`DispatcherService`