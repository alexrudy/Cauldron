.. _ktl:

Keck Telescope Library
----------------------

This section describes how to use the KTL API in your code, and provides a brief overview of the KTL API. A version of the KTL documentation is provided :download:`here </ktl.pdf>`.

Overview
========

The Keck telescope library provides an API for communicating small amounts of data between processes.

KTL provides an API for reading and writing keyword values. To support KTL keywords, applications provide a dispatcher, which responds to read and write requests that it recieves via the KTL backend.

The KTL system relies on a message passing interface and routing system which is complex and composed of a lot of software. In order to use KTL, you must be running on a machine that has the full Lick or Keck Observatory installation call stack. This makes it difficult to write modular tests, and to write code which depends heavily on the KTL library.

Well written instrument code and facility tools will naturally heavily depend on the KTL API to monitor and maintain state, and to provide a control interface. On the other hand, writing an instrument or facility tool with no KTL integration requires that KTL be "bolted-on" during a later phase of development, and can lead a developer to depend on concepts which are not well-suited to the KTL API (such as directly exposing an interpreter). In order to facilitate development with the KTL API, :mod:`Cauldron` was designed to remove the dependency on facility software, and to allow users to write code which runs just as well in the real environment as it does in test environments.

The KTL API can be thought of as a message passing interface, with essentially two types of messages:

1. Read/show messages, where a client is requesting the current value of a keyword.
2. Write/modify messages, where a client is requesting that the current value of a keyword be changed.

Messages are passed in ASCII encoded strings on the backend, with type checking (at least for :mod:`Cauldron`) only enforced by the frontend code. Type checking in the real KTL environemnt can also be done by the message passing interface.

Keywords and services are discovered via XML configuration files on the KTL backend, and support for KTL XML files is possible, but not implemented, in :mod:`Cauldron`.

The KTL API is implemented by two entities, Clients and Dispatchers. Clients are user-facing entities which read and write keyword values. Dispatchers are the facility-facing tools which respond to read and write requests.

Clients
=======

KTL Clients can read and write to keyword values. In python, KTL clients are implemented via :mod:`ktl`, and have an object-oriented and procedural interface. :mod:`Cauldron` implements the bare bones of the object-oriented interface, and could be easily modified to include further KTL features or a broader procedural interface. Clients are used by code which does not "own" the keyword values.

To use a client in the object-oriented fashion, initialize a service, and access that service like a dictionary of keywords::
    
    >>> from Cauldron.ktl import Service
    >>> svc = Service("MyCauldronService")
    >>> kwd = svs["MYKEYWORD"]
    >>> kwd.write(10)
    >>> print(kwd.read())
    10
    

The available methods for :class:`Service <Cauldron.base.client.ClientService>` and :class:`Keyword <Cauldron.base.client.ClientKeyword>` are documented in :mod:`Cauldron.base`. Using the Client library requires that the dispatcher-side of the library is running somewhere.

Dispatchers
===========

KTL Dispatchers provide the source of values, and respond to requests to read and write from a particular keyword. Dispatchers must repsond to all requests, but don't have to do anything on a given request, including saving a given keyword value. Using a dispatcher is a little more complicated. To start a dispatcher, you must define a function which will be called with a single argument, the :class:`Service <Cauldron.base.dispatcher.DispatcherService>` instance, and will create all of the required :class:`Keyword <Cauldron.base.dispatcher.DispatcherKeyword>` instances::
    
    from Cauldron.DFW import Service, Keyword
    
    def setup(service):
        Keyword("MYKEYWORD", service)
        
    service = Service('MyCauldronService', 'path/to/stdiosvc.conf', setup, 'name-of-dispatcher')
    
    kwd = service["MYKEYWORD"]
    kwd.modify("hello")
    
