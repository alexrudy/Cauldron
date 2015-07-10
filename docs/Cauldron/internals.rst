.. _internals:

Cauldron Internals
******************

.. automodapi:: Cauldron.types

.. automodapi:: Cauldron.exc

.. automodapi:: Cauldron.compat

KTL API Features
----------------

KTL API features which depend only on the base classes :class:`~Cauldron.base.client.ClientService`, :class:`~Cauldron.base.client.ClientKeyword`, :class:`~Cauldron.base.dispatcher.DispatcherService` and :class:`~Cauldron.base.dispatcher.DispatcherKeyword` can be implemented inside the private :mod:`_ktl` and :mod:`_DFW` modules, which provide the implementation for the KTL API. The only exception are subclasses of :class:`~Cauldron.base.client.ClientKeyword` or :class:`~Cauldron.base.dispatcher.DispatcherKeyword`, which should be implemented in :mod:`Cauldron.types`, and should use the :func:`~Cauldron.types.dispatcher_keyword` and :func:`~Cauldron.types.client_keyword` decorators in :mod:`Cauldron.types`.

Within these special hidden modules, you may use relative imports to import the implemented *Keyword* and *Service* classes, and those imports will work correctly to find the concrete implementations which belong to your backend of choice. To setup additional features of the KTL API which depend on runtime state, you can use the setup API functions.

API Setup Functions
-------------------

.. autofunction:: Cauldron.api.register_client_setup

.. autofunction:: Cauldron.api.register_dispatcher_setup