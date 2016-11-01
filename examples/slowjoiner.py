#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import time
import click
from Cauldron.types import Basic
import lumberjack
import Cauldron
from Cauldron.zmq.broker import ZMQBroker
from Cauldron.api import STRICT_KTL_XML, use

class SlowThing(Basic):
    """Slowly do stuff."""
    
    def write(self, value):
        """Take the action required for a write."""
        time.sleep(float(value))

def setup(service):
    """Set up the KTL service with some dummy keywords."""
    SlowThing("SLOWTHING", service, initial=0.0)

def server(shutdown, running, service='saotest'):
    """Server to serve KTL keywords"""
    from Cauldron import DFW
    svc = DFW.Service(service, None, setup=setup)
    server.svc = svc
    try:
        running.set()
        while not shutdown.is_set():
            shutdown.wait(300)
    finally:
        svc.shutdown()
    

def client(service):
    """Client side of things."""
    from Cauldron import ktl
    svc = ktl.Service(service)
    try:
        kw = svc['SLOWTHING']
        kw.write('4.0', wait=False)
    finally:
        svc.shutdown()
    
@click.command()
@click.option("-k", "--backend", type=str, default="local", help="KTL Backend")
def main(backend):
    """Main command."""
    lumberjack.setup_logging('stream')
    Cauldron.configuration.set("zmq", "pool", "2")
    Cauldron.configuration.set("core", "timeout", "1.0")
    Cauldron.configuration.set("zmq", "error-on-join-timeout", "no")
    Cauldron.configuration.set("zmq", "broker", "inproc://broker")
    Cauldron.configuration.set("zmq", "publish", "inproc://publish")
    Cauldron.configuration.set("zmq", "subscribe", "inproc://subscribe")
    STRICT_KTL_XML.off()
    if backend == 'zmq':
        b = ZMQBroker.sub()
    Cauldron.use(backend)
    SERVICE = 'saotest'
    shutdown = threading.Event()
    running = threading.Event()
    thread = threading.Thread(target=server, args=(shutdown, running, SERVICE))
    thread.start()
    try:
        running.wait(10)
        if running.is_set():
            client(SERVICE)
    finally:
        shutdown.set()
        for t in threading.enumerate():
            print(repr(t))
        thread.join()
    
    
    
if __name__ == '__main__':
    main()
    