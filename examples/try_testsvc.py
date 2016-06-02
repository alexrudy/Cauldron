#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A simple dispatcher for testsvc
"""

from Cauldron.api import use, install
import time
use("zmq")
install()

from Cauldron import DFW

def setup(service):
    """Setup the keywords"""
    DFW.Keyword.types['integer']("TTCAMX", service)

svc = DFW.Service("testsvc", None, setup=setup)
kwd = svc['TTCAMX']

while True:
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        break
    
svc.shutdown()