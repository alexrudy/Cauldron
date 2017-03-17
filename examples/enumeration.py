#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import click
import contextlib

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
    
@click.command()
@click.option("--dispatcher/--no-dispatcher", default=False, help="Run a dispatcher.")
@click.option("-k", "--backend", default='local', help='The Cauldron backend to select.')
@click.option("-s", "--service", default='saotest', help="Service to test against.")
@click.option("--keyword", type=str, default="WFSCENTROID", help="Keyword to examine.")
@click.option("-n", type=int, default=3, help="Number of enumerations to examine.")
def main(keyword, n, dispatcher, backend, service):
    """Test against an enumerated keyword."""
    import Cauldron
    Cauldron.use(backend)
    with dispatch(dispatcher, service):
        client(service, keyword, n)
    
if __name__ == '__main__':
    main()
    