#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import time
import click
from Cauldron.types import Basic
import lumberjack
import contextlib
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

@contextlib.contextmanager
def server(service='saotest'):
    """Server to serve KTL keywords"""
    from Cauldron import DFW
    svc = DFW.Service(service, None, setup=setup)
    with svc:
        yield svc
    

def client(service):
    """Client side of things."""
    from Cauldron import ktl
    svc = ktl.Service(service)
    kw = svc['SLOWTHING']
    kw.write('4.0', wait=False)
    click.echo("Client finishes write.")
    
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
    with server(SERVICE):
        client(SERVICE)
        click.echo("Done with client.")
        click.echo("Threads:")
        for i,t in enumerate(threading.enumerate()):
            click.echo("{0:d}) {1}".format(i,t))
    
    
    
if __name__ == '__main__':
    main()
    