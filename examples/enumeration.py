#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import click
import contextlib
import logging

def setup(service):
    """Set up the KTL service with some dummy keywords."""
    from Cauldron import DFW
    DFW.Keyword.types['boolean']('WFSCAMSTATE', service, initial=True)
    kwd = DFW.Keyword.types['enumerated']('WFSCENTROID', service, initial='0')
    kwd.mapping[0] = 'COG'
    kwd.mapping[1] = 'QUAD'
    kwd.mapping[2] = 'BINQUAD'

@contextlib.contextmanager
def dispatch(run, service='saotest'):
    """Server to serve KTL keywords"""
    if run:
        from Cauldron import DFW
        svc = DFW.Service(service, None, setup=setup)
    try:
        yield
    finally:
        if run:
            svc.shutdown()
    

def client(service, keyword, n):
    """Client side of things."""
    from Cauldron import ktl
    svc = ktl.Service(str(service))
    kw = svc[str(keyword)]
    template = "{0!s:20s} | {1:20s} | {2:10s} | {3:10s}"
    click.echo("# " + template.format('binary', 'type', 'ascii', 'ascii-type'))
    initial = kw.read()
    try:
        click.echo("  " + template.format(kw['binary'], type(kw['binary']), kw['ascii'], type(kw['ascii'])))
        for i in range(n):
            kw.write(i, binary=True)
            kw.read()
            click.echo("  " + template.format(kw['binary'], type(kw['binary']), kw['ascii'], type(kw['ascii'])))
    finally:
        kw.write(initial, wait=False)
    
@contextlib.contextmanager
def broker():
    """Broker runner."""
    from Cauldron import registry
    from Cauldron.zmq.broker import ZMQBroker
    if registry.dispatcher.backend == "zmq":
        b = ZMQBroker.thread()
    try:
        yield
    finally:
        if registry.dispatcher.backend == "zmq":
            b.stop()
    
def configure():
    """Configure Cauldron"""
    from Cauldron.config import cauldron_configuration
    cauldron_configuration.set("zmq", "broker", "inproc://broker")
    cauldron_configuration.set("zmq", "publish", "inproc://publish")
    cauldron_configuration.set("zmq", "subscribe", "inproc://subscribe")
    cauldron_configuration.set("zmq", "pool", "2")
    cauldron_configuration.set("zmq", "timeout", "5")
    cauldron_configuration.set("core", "timeout", "5")
    
def logging_level(f):
    """Logging arguments."""
    f = click.option("--verbose", "level", flag_value=logging.NOTSET, help="Use verbose logging.")(f)
    f = click.option("--debug", "level", flag_value=logging.DEBUG, help="Use debug logging.")(f)
    f = click.option("--info", "level", default=True, flag_value=logging.INFO, help="Default logging.")(f)
    f = click.option("--quiet", "level", flag_value=logging.ERROR, help="Make things quiet.")(f)
    return f
    
@click.command()
@click.option("--dispatcher/--no-dispatcher", default=False, help="Run a dispatcher.")
@click.option("-k", "--backend", default='local', help='The Cauldron backend to select.')
@click.option("-s", "--service", default='saotest', help="Service to test against.")
@click.option("--keyword", type=str, default="WFSCENTROID", help="Keyword to examine.")
@click.option("-n", type=int, default=3, help="Number of enumerations to examine.")
@logging_level
def main(keyword, n, dispatcher, backend, service, level):
    """Test against an enumerated keyword."""
    import Cauldron
    import lumberjack
    lumberjack.setup_logging(mode='stream', level=level)
    log = logging.getLogger()
    log.setLevel(level)
    
    configure()
    Cauldron.use(backend)
    with broker(), dispatch(dispatcher, service):
        client(service, keyword, n)
    
if __name__ == '__main__':
    main()
    