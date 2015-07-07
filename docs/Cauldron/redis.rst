.. module:: Cauldron.redis

*********************
Redis-backed Keywords
*********************

A KTL-like service based on REDIS_. REDIS_ is a key-value store, designed to be lightweight and fast. To use REDIS_ as the KTL backend for ShadyAO, simply start a REDIS_ server, and configure your connection appropriately. For a simple localhost configuration, this looks like::
    
    [redis]
    host = localhost
    port = 6379
    db = 0
    

REDIS_ has two primary weaknesses as a KTL backend. REDIS_ doesn't provide key types, so all keys are typed as strings. Type consistency is enforced by :mod:`ShadyAO`, but not by the REDIS_ backend, which means that you can set a key to an invalid value via the KTL-based interfaces to :mod:`ShadyAO`. As well, KTL doesn't verify that keys must exist, so it is easy to write to a non-existent key which isn't being listened to by :mod:`ShadyAO`.

.. _REDIS: http://redis.io

Reference/API
-------------

.. automodapi:: Cauldron.redis.service

.. automodapi:: Cauldron.redis.keyword