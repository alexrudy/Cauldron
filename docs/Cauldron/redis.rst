.. module:: Cauldron.redis

*********************
Redis-backed Keywords
*********************

A KTL-like service based on REDIS_. REDIS_ is a key-value store, designed to be lightweight and fast.

REDIS_ has a few weaknesses as a KTL backend. REDIS_ doesn't provide key types, so all keys are typed as strings, and REDIS_ doesn't provide an easy way for the dispatcher to notify the user of a poorly-formatted keyword.

.. _REDIS: http://redis.io

Reference/API
-------------

.. automodapi:: Cauldron.redis.client

.. automodapi:: Cauldron.redis.dispatcher