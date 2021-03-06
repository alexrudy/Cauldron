Cauldron
--------

.. image:: https://travis-ci.org/alexrudy/Cauldron.svg?branch=master
    :target: https://travis-ci.org/alexrudy/Cauldron

.. image:: https://coveralls.io/repos/alexrudy/Cauldron/badge.svg?branch=master
    :target: https://coveralls.io/github/alexrudy/Cauldron?branch=master
    
.. image:: https://readthedocs.org/projects/cauldron/badge/?version=latest
    :target: http://cauldron.readthedocs.io/en/latest/?badge=latest

Cauldron is a library to remove the dependency on the "Keck Telescope Libary", KTL.

KTL is a system used by UC Observatories for both Lick and Keck Observatories. It is primarily
a message passing system which behaves akin to a Keyword-Value store with distributed backends.

KTL uses come in two flavors: "Clients", which read and write to a KTL service, and "Dispatchers",
which maintain the truth value of keywords for a given service.

This library provides a python drop-in replacement for both clients and dispatchers which use the
KTL libraries and protocols. It is designed to seamlessly replace the need for KTL tools when
running on a local, non-production machine.


Installation
============

Cauldron is a standard python package which uses setuptools. It uses the ``astropy`` setuptools
which fix some bugs and provide some nice documentation advantages. This does mean that `Cauldron`
depends on ``astropy``, though this is an installation and test dependency, not a runtime dependency.

Cauldron also depends on the ``six`` module. Some Cauldron backends depend on other third party modules.
To install all third party modules, you can use ``pip``::
    
    $ pip install -r requirements.txt
    

To install Cauldron, navigate to the Cauldron source directory, then do a standard setuptools installation::
    
    $ cd /my/copy/of/cauldron/
    $ python setup.py install
    

Using Cauldron
==============

To use Cauldron, you must first select a backend::
    
    import Cauldron
    Cauldron.use("local")
    

Then, where you would have imported a KTL library, you can call::
    
    from Cauldron import ktl
    

or for the python dispatcher framework::
    
    from Cauldron import DFW
    

To use the standard KTL implementation, use the "ktl" backend::
    
    import Cauldron
    Cauldron.use("ktl")
    
To use existing code which doesn't follow the ``from Cauldron import DFW``-style, you
can "install" the Cauldron modules into their default place on the system.::
    
    from Cauldron.api import install
    install()
    
You should do this before your code imports ``ktl`` or ``DFW``. This is a very hacky way
to install a module at runtime. Then again, most of Cauldron is a giant runtime hack, so your
mileage may vary.

Once you have done this, code which imports ``ktl`` or ``DFW`` will get the Cauldron versions, so
the following will work::
    
    import ktl, DFW
    

Documentation
=============

Documentation is available on ReadTheDocs at http://cauldron.readthedocs.org/en/latest/Cauldron/index.html.

Sphinx documentation is provided in the ``docs/`` folder of the source code. To build it you will need sphinx installed.
Then run::

    $ cd docs/
    $ make html


Limitations
===========

Cauldron is very limited. I've written it only to replicate the bare minimum of what I need from both ``ktl`` and ``DFW``. If you need more, implement it!
