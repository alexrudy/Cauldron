#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demonstrate ZMQ read-write ability.
"""
import time
from lumberjack import setup_logging
from logging import getLogger

setup_logging(mode='stream', level=5)
log = getLogger("example.zmq")

# Pick a backend.
from Cauldron.api import use
use("zmq")

# Get ready!
from Cauldron.config import get_configuration
config = get_configuration()
config.set("zmq", "broker", "inproc://broker")
config.set("zmq", "publish", "inproc://publish")
config.set("zmq", "subscribe", "inproc://subscribe")
# config.set("zmq", "pool", "2")
# config.set("zmq", "autobroker", "yes")
# config.set("core", "timeout", "5")

try:

    from Cauldron import DFW
    disp = DFW.Service("testsvc", config=None)
    dtest = disp["TEST"]
    log.info(dtest)

    from Cauldron import ktl
    svc = ktl.Service("testsvc", populate=True)
    log.info(svc)
    log.info(svc.populated())
    log.info("Done!")
    disp.shutdown()
    log.info("Shutdown complete.")
finally:
    import threading
    for thread in threading.enumerate():
        print(thread)