Changes to Cauldron
-------------------

0.3.0
=====
- First proper release of Cauldron, including fixing version number.
- ZMQ Backend implemented for single-dispatcher systems.
- REDIS Backend has some handling for asynchronus calls.
- Support for typed keywords, following the KTL type conventions. No support yet for arrays or masks.
- Feature registration system for better management of backends and keyword types.
- A global Cauldron configuration system, so that configurations apply transparently to clients as well as servers.