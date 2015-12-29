Changes to Cauldron
-------------------

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