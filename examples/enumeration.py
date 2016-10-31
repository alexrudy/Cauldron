#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

def setup(service):
    """Set up the KTL service with some dummy keywords."""
    from Cauldron import DFW
    DFW.Keyword.types['boolean']('WFSCAMSTATE', service, initial=True)
    kwd = DFW.Keyword.types['enumerated']('WFSCENTROID', service, initial='0')
    kwd.mapping[0] = 'COG'
    kwd.mapping[1] = 'QUAD'
    kwd.mapping[2] = 'BINQUAD'

def server(shutdown, running, service='saotest'):
    """Server to serve KTL keywords"""
    from Cauldron import DFW
    svc = DFW.Service(service, None, setup=setup)
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
        kw = svc['WFSCENTROID']
        print("# binary, ascii")
        for i in range(3):
            kw.write(i)
            kw.read()
            print(kw['binary'], kw['ascii'])
        
    finally:
        svc.shutdown()
    

def main():
    """Main command."""
    import Cauldron
    from Cauldron.api import STRICT_KTL_XML
    STRICT_KTL_XML.off()
    Cauldron.use("local")
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
        thread.join()
    
if __name__ == '__main__':
    main()
    