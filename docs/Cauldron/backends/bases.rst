.. module:: Cauldron.base

Cauldron KTL base classes
*************************

The KTL API is defined in :mod:`Cauldron` by four abstract base classes, :class:`~Cauldron.base.client.ClientService`, :class:`~Cauldron.base.client.ClientKeyword`, :class:`~Cauldron.base.dispatcher.DispatcherService` and :class:`~Cauldron.base.dispatcher.DispatcherKeyword`. These base classes are used with a concrete backend implementation, and are available in :mod:`Cauldron.ktl` and :mod:`Cauldron.DFW` at runtime.

These classes are designed to provide a consistent API for KTL services and keywords, irrespective of the KTL backend. They require that various user-facing functions and private functions are implemented, and they specify which functions are not required by the Cauldron KTL API.

.. note:: Not all KTL API features are implemented in Cauldron, and not all KTL python API functions are available. It is relatively trivial to implement new python API functions (e.g. the procedural KTL interface) using the existing Cauldron modules. Implementing new API features is more difficult.

Reference/API
=============

.. automodapi:: Cauldron.base.client

.. automodapi:: Cauldron.base.dispatcher

