.. module:: Cauldron.zmq

************
ZMQ Keywords
************

ZeroMQ_ is a lightweight reliable messaging protocol. This backend provides a messaging framework which handles keywords based on the ZeroMQ_ protocol.

ZeroMQ_ has a single primary weakness as a backend: like real-world KTL, it requires a centralized message "router" which can direct clients to the dispatchers of their choice. Since such routing is a complicated process, the ZeroMQ_ backend currently makes no attempt to support services with multiple or distinguishable dispatchers. To solve the routing problem, the ZMQ backend implements a "Router" object which tells clients where to find appropriate services. Dispatchers must register with a broker, and if no brokers are available, then dispatchers may try to create a broker.

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
    publish = 6511
    broadcast = 6512
    broker = 6513
    timeout = 5
    mode = broker
    

Note that ZMQ requires three separate networking ports to distinguish between sequential commands (commands which require a response) and broadcast commands (which do not require a response).


Reference/API
=============

.. automodapi:: Cauldron.zmq.common

.. automodapi:: Cauldron.zmq.client

.. automodapi:: Cauldron.zmq.dispatcher

.. automodapi:: Cauldron.zmq.broker

.. _ZeroMQ: http://zeromq.org
