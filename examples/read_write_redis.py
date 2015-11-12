#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demonstrate REDIS read-write ability.
"""
import time
from lumberjack import setup_logging
setup_logging(mode='stream')
from logging import getLogger
from Cauldron.conftest import clear_registry
log = getLogger("example.redis")
# Start up!
from Cauldron.redis.common import configure_pool, REDIS_SERVICES_REGISTRY
configure_pool(host='localhost', port=6379, db=0)
clear_registry()

# Get ready!
from Cauldron.api import use
use("redis")

from Cauldron import DFW
disp = DFW.Service("testsvc", config=None)
dtest = disp["TEST"]
log.info(dtest)

from Cauldron import ktl
svc = ktl.Service("testsvc")
test = svc["TEST"]
log.info("Writing")
test.write("SOMEVALUE")
log.info(test.read())
log.info("Done!")
disp.shutdown()