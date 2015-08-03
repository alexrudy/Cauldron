# -*- coding: utf-8 -*-
"""
Tests specific to the local backend.
"""

import pytest
pytestmark = pytest.mark.usefixtures("teardown_cauldron")

from ..conftest import fail_if_not_teardown

@pytest.fixture
def uselocal(request):
    """Use the local backend."""
    from Cauldron.api import use
    use('local')
    request.addfinalizer(fail_if_not_teardown)

@pytest.fixture
def local_service(uselocal, servicename, config):
    """docstring for local_service"""
    from Cauldron.DFW import Service
    svc = Service(servicename, config=config)
    mykw = svc['KEYWORD']
    return svc
    
@pytest.fixture
def local_client(local_service, servicename):
    """Test a client."""
    from Cauldron import ktl
    return ktl.Service(servicename)

def test_duplicate_services(uselocal):
    """Test duplicate services."""
    from Cauldron.DFW import Service
    svc = Service("MYSERVICE", config=None)
    with pytest.raises(ValueError):
        svc2 = Service("MYSERVICE", config=None)
    svc3 = Service.get_service("MYSERVICE")
    assert svc3 is svc
    
def test_client_not_started(uselocal, servicename):
    """Use local, but fail when a client hasn't been started yet."""
    from Cauldron.exc import ServiceNotStarted
    from Cauldron.ktl import Service
    with pytest.raises(ServiceNotStarted):
        Service(servicename)
    
def test_monitor(local_service, local_client):
    """Test monitoring"""
    
    def monitor(keyword):
        """Monitor"""
        monitor.monitored = True
        print("Monitored!")
    
    monitor.monitored = False
    
    local_client["KEYWORD"].callback(monitor)
    local_client["KEYWORD"].monitor(prime=False)
    assert len(local_client['KEYWORD']._callbacks) == 1
    assert not monitor.monitored
    assert len(local_service["KEYWORD"]._consumers) == 1
    local_service["KEYWORD"].modify("SomeValue")
    assert monitor.monitored
    local_client["KEYWORD"].callback(monitor, remove=True)
    assert len(local_client['KEYWORD']._callbacks) == 0
    local_client["KEYWORD"].callback(monitor, preferred=True)
    local_client["KEYWORD"].monitor(prime=True)
    local_client["KEYWORD"].monitor(start=False)
    assert len(local_service['KEYWORD']._consumers) == 0
    
def test_subscribe(local_service, local_client):
    """Test monitoring"""
    
    def monitor(keyword):
        """Monitor"""
        monitor.monitored = True
        print("Monitored!")
    
    monitor.monitored = False
    
    local_client["KEYWORD"].callback(monitor)
    local_client["KEYWORD"].subscribe(prime=False)
    assert len(local_client['KEYWORD']._callbacks) == 1
    assert not monitor.monitored
    assert len(local_service["KEYWORD"]._consumers) == 1
    local_service["KEYWORD"].modify("SomeValue")
    assert monitor.monitored
    
def test_write_async(local_service, local_client, recwarn):
    """Test local asynchronous write."""
    from Cauldron.exc import CauldronAPINotImplementedWarning
    local_client["KEYWORD"].write("10", wait=False)
    w = recwarn.pop()
    assert w.category == CauldronAPINotImplementedWarning
    
def test_read_async(local_client, recwarn):
    """Test local asynchronous read."""
    from Cauldron.exc import CauldronAPINotImplementedWarning
    local_client["KEYWORD"].read(wait=False)
    w = recwarn.pop()
    assert w.category == CauldronAPINotImplementedWarning
    
def test_wait(local_client):
    """Test local wait()"""
    from Cauldron.exc import CauldronAPINotImplemented
    with pytest.raises(CauldronAPINotImplemented):
        local_client["KEYWORD"].wait()
        

def test_readonly(local_client, local_service):
    """Test a read only keyword."""
    local_service['ROKEYWORD'].readonly = True
    with pytest.raises(ValueError):
        local_client['ROKEYWORD'].write("10")
        
def test_writeonly(local_client, local_service):
    """Test a read only keyword."""
    local_service['WOKEYWORD'].writeonly = True
    with pytest.raises(ValueError):
        local_client['WOKEYWORD'].read()