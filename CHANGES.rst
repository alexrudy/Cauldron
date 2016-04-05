Changes to Cauldron
-------------------

0.5.2
=====
- Fixed a bug in ZMQ addressing to properly specify
- Console script implementations of ``modify`` and ``show``.
- Improved ``ktl.procedural`` to match most features of the original. (Some no-ops are not implemented.)

0.5.1
=====
- Asynchronous support in ZMQ backend. (Quasi, network requests still happen serially.)
- Better setup for standard ktl, supports the Cauldron keyword type interface.
- XML support is improved when STRICT_KTL_XML is not enabled.
- Primitive support for python3 (uses 2to3 for bundeled packages.)
- Support for python2.6 even though astropy dropped support for it.
- Tests more consistently generate keyword names.
- Documentation improvements.

0.5.0
=====
- Consistent backend registration API, which uses the ``Cauldron.backends`` entry point.
- ZMQ uses a broker instead of a router to handle multiple dispatchers.
- Improvements to the keyword type handling system in preparation for use with real KTL


0.4.0
=====
- Removed REDIS backend. It was causing too many deadlock problems, and isn't a fundamentally good communication protocol for KTL.
- Implemented keyword types for Clients and for Orphan keywords in the dispatcher.
- Extension command keyword: Using a boolean keyword, implement a keyword which simply triggers a function.
- Added null handlers to loggers for Cauldron (Cauldron, DFW, ktl)
- Descriptor Events implement argument passing to allow callbacks to change the returned value.
- Implemented KTL type aliases when necessary (e.g. 'float' and 'double' are implemented identically in python.)

0.3.0
=====
- First proper release of Cauldron, including fixing version number.
- ZMQ Backend implemented for single-dispatcher systems.
- REDIS Backend has some handling for asynchronous calls.
- Support for typed keywords, following the KTL type conventions. No support yet for arrays or masks.
- Feature registration system for better management of backends and keyword types.
- A global Cauldron configuration system, so that configurations apply transparently to clients as well as servers.