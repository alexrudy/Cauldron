.. module:: Cauldron.base

Cauldron KTL API
****************

The KTL API is defined in :mod:`Cauldron` by four abstract base classes, :class:`~client.ClientService`, :class:`~client.ClientKeyword`, :class:`~dispatcher.DispatcherService` and :class:`~dispatcher.DispatcherKeyword`. These base classes are used with a concrete backend implementation, and are available in :mod:`Cauldron.ktl` and :mod:`Cauldron.DFW` at runtime.

These classes are designed to provide a consistent API for KTL services and keywords, irrespective of the KTL backend. They require that various user-facing functions and private functions are implemented, and they specify which functions are not required by the Cauldron KTL API.

.. note:: Not all KTL API features are implemented in Cauldron, and not all KTL python API functions are available. It is relatively trivial to implement new python API functions (e.g. the procedural KTL interface) using the existing Cauldron modules. Implementing new API features is more difficult.

API Implementation Status
=========================

A brief summary of major KTL API features is provided in the table below. API features marked as *Planned* are ones that I do intend to implement at some point in support of ShadyAO. API features marked as *Not Implemented* would require more work.

======================== ===================
Feature                  Status
======================== ===================
Synchronous read/write   Implemented
Asynchronous read/write  Not Implemented
Heartbeats               *Planned*
Callbacks                Implemented
Polling                  Not Implemented
Scheduling               Not Implemented
Expressions              Not Implemented
XML Keyword Validation   *Planned*
Operator Overloading     Not Implemented
======================== ===================

When Cauldron does not implement a feature, using that feature will raise an :exc:`CauldronAPINotImplemented` error, which is a subclass of :exc:`NotImplementedError`.

Reference/API
=============

.. automodapi:: Cauldron.base.client

.. automodapi:: Cauldron.base.dispatcher
