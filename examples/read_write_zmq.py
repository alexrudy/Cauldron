#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demonstrate REDIS read-write ability.
"""
import time
from lumberjack import setup_logging, setup_warnings_logger
from logging import getLogger

setup_logging(mode='stream', level=5)
setup_warnings_logger("")
log = getLogger("example.zmq")

# Get ready!
from Cauldron.api import use
use("zmq")

from Cauldron import DFW

def setup(service):
    """Setup the service."""
    kwd = DFW.Keyword.Keyword("TEST", service)
    print("Service setup")

disp = DFW.Service("testsvc", setup = setup, config=None)
dtest = disp["TEST"]
log.info("Dispatcher Keyword {0!r}".format(dtest))

VALUE = "SOMEVALUE"
time.sleep(1.0)
log.info("Starting KTL client...")
from Cauldron import ktl
svc = ktl.Service("testsvc")
log.info("Getting KTL keyword object...")
test = svc["TEST"]
log.info("Writing '{0}'".format(VALUE))
test.write(VALUE)
log.info("'{0}' =? '{1}'".format(VALUE, test.read()))
log.info("Done!")
svc
disp.shutdown()
log.info("Shutdown complete.")
import zmq
ctx = zmq.Context.instance().destroy()
disp.shutdown()

log.info("Context terminated.")
