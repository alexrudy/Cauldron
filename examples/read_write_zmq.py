#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demonstrate REDIS read-write ability.
"""
import time, threading
from lumberjack.config import configure
from logging import getLogger

configure('stream')
log = getLogger("example.zmq")

from Cauldron.config import get_configuration
config = get_configuration()
config.set("zmq", "broker", "inproc://broker")
config.set("zmq", "publish", "inproc://publish")
config.set("zmq", "subscribe", "inproc://subscribe")
# config.set("zmq", "pool", "2")
config.set("zmq", "autobroker", "yes")

# Get ready!
from Cauldron.api import use
use("zmq")


from Cauldron import DFW

def slow(kwd):
    """Make something slow."""
    print("Being slow!")
    time.sleep(1.0)
    print("Done Being slow!")
    

def setup(service):
    """Setup the service."""
    kwd = DFW.Keyword.Keyword("TEST", service)
    kwd.callback(slow)
    print("Service setup")

disp = DFW.Service("testsvc", setup = setup, config=None)
dtest = disp["TEST"]
log.info("Dispatcher Keyword {0!r}".format(dtest))

VALUE = "SOMEVALUE"
time.sleep(1.0)
log.info("Starting KTL clients...")
from Cauldron import ktl
svc = ktl.Service("testsvc")
log.info("Getting KTL keyword object...")
test = svc["TEST"]
log.info("Writing '{0}'".format(VALUE))
seq = test.write(VALUE, wait=False)
test.wait(sequence=seq)
log.info("'{0}' =? '{1}'".format(VALUE, test.read()))
seq = test.write(VALUE+"1", wait=False, timeout=0.1)
try:
    success = test.wait(sequence=seq, timeout=0.1)
except Exception as e:
    print(e)

RVALUE = ktl.read("testsvc", "TEST")
log.info("'{0}' =? '{1}'".format(VALUE, RVALUE))

for thread in threading.enumerate():
    print(repr(thread))

log.info("Done!")
svc.shutdown()
disp.shutdown()
log.info("Shutdown complete.")

for thread in threading.enumerate():
    print(repr(thread))

# log.warning("Terminating context.")
# import zmq
# ctx = zmq.Context.instance().destroy()
# log.info("Context terminated.")
