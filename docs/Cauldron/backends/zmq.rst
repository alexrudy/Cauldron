.. module:: Cauldron.zmq

************
ZMQ Keywords
************

ZeroMQ_ is a lightweight reliable messaging protocol. This backend provides a messaging framework which handles keywords based on the ZeroMQ_ protocol.

ZeroMQ_ has a single primary weakness as a backend: like real-world KTL, it requires a centralized message "router" which can direct clients to the dispatchers of their choice. Since such routing is a complicated process, the ZeroMQ_ backend currently makes no attempt to support services with multiple or distinguishable dispatchers. To solve the routing problem, the ZMQ backend implements a "Router" object which tells clients where to find appropriate services. Dispatchers must register with a router, and if no routers are available, then dispatchers may try to create a router. See :ref:`zmq-routers`

ZeroMQ_ is one of the more robust network backends as the clients talk directly to the dispatcher, and client commands are handled by the dispatcher in a blocking fashion.

The primary caveat when

.. _zmq-config:

Configuring ZMQ
===============

ZeroMQ_ works over network protocols and ports, and so requires some configuration. All configuration happens in a configuration file. The path to the configuration file should be passed to the dispatcher as the *config* argument, and can be passed to the service via the global configuration utilities.


In the most simple case, ZMQ can be configured for a single dispatcher service::
    
    [zmq]
    host = localhost
    protocol = tcp
    dispatch-port = 6511
    broadcast-port = 6512
    

Note that ZMQ requires two separate networking ports to distinguish between sequential commands (commands which require a response) and broadcast commands (which do not require a response).

To configure a router, give the router its own address::
    
    [zmq-router]
    enable = yes
    host = localhost
    protocol = tcp
    port = 6510
    first-port = 6600
    last-port = 6700
    
    timeout = 1000
    verbose = 0
    process = thread
    allow-spawn = yes

The Router can be entirely disabled (relying on the root configuration in the *zmq* section) by setting ``enable = no``. The last four arguments bear additional explanation here. *timeout* sets the socket timeout for router monitoring commands, in milliseconds. *verbose* can be an integer from 0 to 3 which sets the verbosity of the router process. A value for *verbose* of 1 through 3 will attempt to connect to the router logger. *process* sets the default method for spawning routers as subprocesses of dispatchers. When ``process = thread``, the router will use python's built-in threading. When set to anything else, python multiprocessing will be used for full parallelism.

.. _zmq-routers:
.. program:: Cauldron-router-zmq

ZMQ Routers
===========

ZMQ dispatchers and clients connect directly over a network socket. Each dispatcher requires two addresses (by necessity, at the same host), one for synchronous commands, and one for asynchronous commands. As each dispatcher must have a pair of unique addresses, and clients must be able to locate these unique addresses, the concept of a ZMQ router is introduced. The router acts as an address book to connect clients to services.

Routers can be started from the command line via the :program:`Cauldron-router-zmq` script. This script starts a ZMQ router to connect clients to dispatchers. It must be started before any client or dispatcher starts.

.. option:: -v

    Use up to three ``-v`` options to increase the verbosity of the router.
    
.. option:: -c <path/to/config>
    
    Provide an alternate configuration file name.

Reference/API
=============

.. automodapi:: Cauldron.zmq.common

.. automodapi:: Cauldron.zmq.client

.. automodapi:: Cauldron.zmq.dispatcher

.. automodapi:: Cauldron.zmq.router

.. _ZeroMQ: http://zeromq.org
