Cauldron
========

Cauldron is a library to remove the dependency on the "Keck Telescope Libary", KTL.

KTL is a system used by UC Observatories for both Lick and Keck Observatories. It is primarily
a message passing system which behaves akin to a Keyword-Value store with distributed backends.

KTL uses come in two flavors: "Clients", which read and write to a KTL service, and "Dispatchers",
which maintain the truth value of keywords for a given service.

This library provides a python drop-in replacement for both clients and dispatchers which use the
KTL libraries and protocols. It is designed to seamlessly replace the need for KTL tools when
running on a local, non-production machine.

Cauldron is available on GitHub: https://github.com/alexrudy/Cauldron.

.. toctree::
  :maxdepth: 1
  
  Cauldron/index.rst
