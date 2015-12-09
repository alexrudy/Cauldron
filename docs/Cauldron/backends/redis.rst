.. module:: Cauldron.redis

*********************
Redis-backed Keywords
*********************

A KTL-like service based on redis_. redis_ is a key-value store, designed to be lightweight and fast.

redis_ has a few weaknesses as a KTL backend. redis_ doesn't provide key types, so all keys are typed as strings, and redis_ doesn't provide an easy way for the dispatcher to notify the user of a poorly-formatted keyword.

To use :mod:`Cauldron.redis`, you should first configure redis_. To configure redis_, provide a redis_ URL in your configuration::
    
    [redis]
    url = redis://localhost:6379/0
    

The redis_ backend will not take any special precautions to flush the database between :mod:`Cauldron` invocations. If this is desired, you should clear the redis_ database manually.

Implementation
==============

The redis_ backend uses the `redis Publsih Subscribe`_ messaging paradigm to send and recieve ``MODIFY`` commands. As well, the backend uses `Keyspace Notifications`_ to ``BROADCAST`` keyword value changes to all clients. The current value of each keyword is stored in the `redis`_ keyword value store, and currently, ``READ`` commands to not pass through the dispatcher's :meth:`~Cauldron.base.dispatcher.Keyword.update` function.

Reference/API
=============

.. automodapi:: Cauldron.redis.common

.. automodapi:: Cauldron.redis.client

.. automodapi:: Cauldron.redis.dispatcher

.. _redis: http://redis.io
.. _redis-py: https://redis-py.readthedocs.org/en/latest/
.. _redis Publsih Subscribe: http://redis.io/topics/pubsub
.. _Keyspace Notifications: http://redis.io/topics/notifications