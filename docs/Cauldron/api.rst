.. module:: Cauldron.api

Cauldron User's API
*******************

Users need to only know a few things about the workings of :mod:`Cauldron`:

1. Select an appropriate backend.
2. Configure the backend, if necessary.
3. Activate the backend **first** in any code which might import KTL API tools.
4. *Optionally* use Cauldron-style imports in your code.

Selecting a backend
===================

Selecting a backend is fairly easy. Currently, there are three availalbe backends:

- ``local``, which uses in-process methods to communicate between clients and dispatchers. This is the appropraite backend for testing environments, but has no ability to do any inter-process communication.
- ``redis``, which uses a REDIS_ service to provide the keyword communication. This is a good backend to use if you are testing multiple components or inter-process communication.
- ``ktl`` or ``DFW``, which uses the real KTL API in the Lick or Keck software environment. This is the backend to use with production code.

Your backend should be something that you chose once per python invocation. It is not easy, nor recommended, to switch backends within a given process. New backends are relatively easy to implement in a minimal form (simple, synchronous reads and writes), and you can learn about this in :ref:`backends`.

Configuring the backend
=======================

Some backends must be configured before use. For example, the REDIS backend requires settings to find the REDIS database instance. You configure the REIDS backend via :func:`~Cauldron.redis.configure_pool`::

    from Cauldron.redis import configure_pool
    configure_pool(host='localhost', port=6379, db=0, socket_timeout=None)


Activate the backend
====================

Before using any KTL API calls, you must activate the backend via :func:`use`::

    from Cauldron import use
    use("local")

If you want to use regular KTL imports in your code, you must also call :func:`install`. :func:`install` overrides :mod:`ktl` and :mod:`DFW` at runtime, so that when you run code like ``from DFW import Service``, you will recieve the Cauldron version of :class:`Service`, not the pure KTL version.::

    from Cauldron import install
    install()

.. warning:: Using :func:`install` performs a runtime hack in ``sys.modules`` that might be unstable. For this reason, unless you have an existing codebase that you absolutely cannot change, you should use :ref:`cauldron-style`.

If you do not call :func:`install`, you'll have to use :ref:`cauldron-style`. This is the pre

.. _cauldron-style:

Cauldron-style imports
======================

When writing code which uses the KTL backend, use a Cauldron-style import to ensure that you recieve the Cauldron version of the KTL API::

    from Cauldron import ktl
    ktl.write('myservice', 'somekeyword', 10)


This will ensure that the backend is set up correctly before allowing you to import :mod:`ktl` or :mod:`DFW`. If you try to import :mod:`ktl` or :mod:`DFW` before you have selected a backend, using Cauldron-style imports will raise an :exc:`ImportError`.

Using Cauldron with a test-suite
================================

If you wish to use :mod:`Cauldron` with a test suite, it can be desirable to select and start a backend at the invocation of each test. This will flush out persistent keyword values from some backends, and will test that the KTL API is started in the correct order. However, :mod:`Cauldron` will try to prevent the user from selecting a backend while one is already in use. To get around this problem, you can use :func:`teardown` to remove the :mod:`Cauldron` backend::
    
    from Cauldron import use, teardown
    use("local")
    teardown()
    use("redis") # +DOCTEST: SKIP

.. _REDIS: http://redis.io

API Reference
=============

.. automodapi:: Cauldron.api
