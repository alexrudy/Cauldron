#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demonstrate REDIS read-write ability.
"""
import time
from lumberjack import setup_logging, setup_warnings_logger
from logging import getLogger

setup_logging(mode='stream', level=10)
setup_warnings_logger("")
log = getLogger("example.zmq")

# Get ready!
from Cauldron.api import use
use("zmq")

from Cauldron import DFW
disp = DFW.Service("testsvc", config=None)
dtest = disp["TEST"]
log.info(dtest)

VALUE = "SOMEVALUE"

from Cauldron import ktl
svc = ktl.Service("testsvc", populate=True)
log.info(svc)
log.info(svc.populated())
log.info("Done!")
disp.shutdown()
log.info("Shutdown complete.")
