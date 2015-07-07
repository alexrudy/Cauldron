.. module:: Cauldron

************************************
Cauldron - Abstraction layer for KTL
************************************

Cauldron is a KTL Compatibility Layer.

It is designed to expose the KTL API and to mimic KTL python modules without using the KTL backend. In order to expose the KTL-like backend, there is an abstract base class which is designed to mimics the API for KTL keywords and services. There are two specific backends implemented to the KTL interface, :mod:`Cauldron.local`, a process-local keyword interface, and :mod:`Cauldron.redis`, a REDIS_ based backend.

.. toctree::
    :maxdepth: 1
    
    api
    local
    redis
    

.. _REDIS: http://redis.io