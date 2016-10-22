#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demonstrate REDIS read-write ability.
"""
import time
from lumberjack import setup_logging, setup_warnings_logger
from logging import getLogger

setup_logging(mode='stream', level=10)
log = getLogger("example.zmq")

# Get ready!
from Cauldron.api import use
use("zmq")
from Cauldron import DFW

for i in range(40):
    log.info("Service Realization {0:d}".format(i))
    disp = DFW.Service("testsvc", config=None)
    dtest = disp["TEST"]
    disp.shutdown()

log.info("Done!")
log.info("Shutdown complete.")
