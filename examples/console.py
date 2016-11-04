#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for consoles.
"""
from Cauldron.api import STRICT_KTL_XML
STRICT_KTL_XML.off()
import threading
import click

class Finalizer(threading.Thread):
    """A thread finalizer."""
    def __init__(self, *args, **kwargs):
        super(Finalizer, self).__init__(*args, **kwargs)
        self.running = threading.Event()
        self.shutdown = threading.Event()
        
    def initializer(self):
        """Initalize the thread."""
        pass
        
    def runloop(self):
        """Run loop for the thread."""
        self.running.set()
        while not self.shutdown.is_set():
            self.shutdown.wait(300)
        
    def run(self):
        """Run the full loop."""
        self.initializer()
        try:
            self.runloop()
        finally:
            self.finalizer()
        
    def finalizer(self):
        """Finalize the thread objects."""
        pass

class Server(Finalizer):
    """A thread with finalization."""
    def __init__(self, *args, **kwargs):
        self.service = kwargs.pop("service")
        super(Server, self).__init__(*args, **kwargs)
        
    def initializer(self):
        """Initialize the service."""
        from Cauldron import DFW
        self._svc = DFW.Service(self.service, None, setup=setup)
        
    def finalizer(self):
        """Shutdown the service."""
        self._svc.shutdown()
        

class Broker(Finalizer):
    """Broker management"""
    
    def initializer(self):
        """Initialize the broker."""
        from Cauldron.zmq.broker import ZMQBroker
        self._b = ZMQBroker.sub()
    
    def finalizer(self):
        """Shutdown the broker."""
        self._b.stop()

def setup(service):
    """Set up the KTL service with some dummy keywords."""
    from Cauldron import DFW
    DFW.Keyword.types['boolean']('WFSCAMSTATE', service, initial=True)
    kwd = DFW.Keyword.types['enumerated']('WFSCENTROID', service, initial='0')
    kwd.mapping[0] = 'COG'
    kwd.mapping[1] = 'QUAD'
    kwd.mapping[2] = 'BINQUAD'

def console(service, notify, nowait, timeout):
    """Console client part."""
    from Cauldron.api import use
    from Cauldron.console import ktl_modify
    ktl_modify(service, ('WFSCAMSTATE', 'True'), ('WFSCENTROID', 'QUAD'), notify=notify, nowait=nowait, timeout=timeout)
    

def broker():
    """Broker runner."""
    from Cauldron import registry
    if registry.dispatcher.backend != "zmq":
        return
    return Broker()
    
def configure():
    """Configure Cauldron"""
    from Cauldron.config import cauldron_configuration
    cauldron_configuration.set("zmq", "broker", "inproc://broker")
    cauldron_configuration.set("zmq", "publish", "inproc://publish")
    cauldron_configuration.set("zmq", "subscribe", "inproc://subscribe")
    cauldron_configuration.set("zmq", "pool", "2")
    cauldron_configuration.set("zmq", "timeout", "5")
    cauldron_configuration.set("core", "timeout", "5")

@click.command()
@click.option("--parallel/--no-parallel", default=False)
@click.option("--wait/--no-wait", default=False)
@click.option("--timeout", type=float, default=1.0)
def main(parallel, wait, timeout):
    """Main command."""
    import lumberjack
    lumberjack.setup_logging(mode='stream')
    configure()
    from Cauldron.api import use
    use("zmq")
    service = 'saotest'
    threads = [broker(), Server(service=service)]
    try:
        for t in threads:
            t.start()
        console(service, parallel, not wait, timeout)
    finally:
        for t in threads:
            t.shutdown.set()
        for t in threads:
            t.join(timeout=10)

if __name__ == '__main__':
    main()