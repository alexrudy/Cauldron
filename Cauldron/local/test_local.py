# -*- coding: utf-8 -*-
"""
Tests specific to the local backend.
"""

import pytest
pytestmark = pytest.mark.usefixtures("teardown_cauldron")
from ..conftest import fail_if_not_teardown
from ..exc import CauldronAPINotImplemented
import warnings

@pytest.fixture
def backend(request):
    """Use the local backend."""
    from Cauldron.api import use
    use('local')
    request.addfinalizer(fail_if_not_teardown)

@pytest.fixture
def local_service(backend, servicename, config, keyword_name):
    """docstring for local_service"""
    from Cauldron.DFW import Service
    svc = Service(servicename, config=config)
    mykw = svc[keyword_name]
    return svc
    
@pytest.fixture
def local_client(local_service, servicename):
    """Test a client."""
    from Cauldron import ktl
    return ktl.Service(servicename)
    
def test_teardown(servicename, teardown_cauldron):
    """Check that teardown really does tear things down, in local mode."""
    from Cauldron.api import teardown, use
    use("local")
    from Cauldron.DFW import Service
    svc = Service(servicename+"2", None)
    svc['MYKEYWORD'].modify('10')
    teardown()
    del svc
    
    use("local")
    from Cauldron.DFW import Service
    svc2 = Service(servicename+"2", None)
    assert svc2['MYKEYWORD'].read() == '10'

def test_duplicate_services(backend, servicename):
    """Test duplicate services."""
    from Cauldron.DFW import Service
    svc = Service(servicename, config=None)
    with pytest.raises(ValueError):
        svc2 = Service(servicename, config=None)
    svc3 = Service.get_service(servicename)
    assert svc3 is svc
    
def test_client_not_started(backend, servicename):
    """Use local, but fail when a client hasn't been started yet."""
    from Cauldron.exc import ServiceNotStarted
    from Cauldron.ktl import Service
    with pytest.raises(ServiceNotStarted):
        Service(servicename)
    
def test_monitor(local_service, local_client, keyword_name):
    """Test monitoring"""
    
    def monitor(keyword):
        """Monitor"""
        monitor.monitored = True
        print("Monitored!")
    
    monitor.monitored = False
    
    local_client[keyword_name].callback(monitor)
    local_client[keyword_name].monitor(prime=False)
    assert len(local_client[keyword_name]._callbacks) == 1
    assert not monitor.monitored
    assert len(local_service[keyword_name]._consumers) == 1
    local_service[keyword_name].modify("SomeValue")
    assert monitor.monitored
    local_client[keyword_name].callback(monitor, remove=True)
    assert len(local_client[keyword_name]._callbacks) == 0
    local_client[keyword_name].callback(monitor, preferred=True)
    local_client[keyword_name].monitor(prime=True)
    local_client[keyword_name].monitor(start=False)
    assert len(local_service[keyword_name]._consumers) == 0
    
def test_recursive_callback(local_service, local_client, keyword_name):
    """Test a recursive callback invoke"""
    def cb(keyword):
        cb.count += 1
        print(keyword,type(keyword))
        keyword.write("OtherValue")
    
    def cb2(keyword):
        print(keyword, type(keyword))
    
    cb.count = 0
    local_client[keyword_name].callback(cb)
    local_client[keyword_name].monitor(prime=False)
    local_service[keyword_name].callback(cb2)
    assert len(local_client[keyword_name]._callbacks) == 1
    assert len(local_service[keyword_name]._consumers) == 1
    local_service[keyword_name].modify("SomeValue")
    assert cb.count == 1
    assert local_client[keyword_name]['ascii'] == "OtherValue"
    assert local_service[keyword_name].value == "OtherValue"

def test_subscribe(local_service, local_client, keyword_name):
    """Test monitoring"""
    
    def monitor(keyword):
        """Monitor"""
        monitor.monitored = True
        print("Monitored!")
    
    monitor.monitored = False
    
    local_client[keyword_name].callback(monitor)
    local_client[keyword_name].subscribe(prime=False)
    assert len(local_client[keyword_name]._callbacks) == 1
    assert not monitor.monitored
    assert len(local_service[keyword_name]._consumers) == 1
    local_service[keyword_name].modify("SomeValue")
    assert monitor.monitored
    
@pytest.mark.xfail(raises=CauldronAPINotImplemented)
def test_wait(local_client, keyword_name):
    """Test local wait()"""
    warnings.filterwarnings('always')
    from Cauldron.exc import CauldronAPINotImplemented
    local_client[keyword_name].wait()
        

def test_readonly(local_client, local_service, keyword_name3):
    """Test a read only keyword."""
    local_service[keyword_name3].readonly = True
    with pytest.raises(ValueError):
        local_client[keyword_name3].write("10")
        
def test_writeonly(local_client, local_service, keyword_name4):
    """Test a read only keyword."""
    local_service[keyword_name4].writeonly = True
    with pytest.raises(ValueError):
        local_client[keyword_name4].read()
    

def test_teardown(servicename, teardown_cauldron, keyword_name2, servicename2):
    """Check that teardown really does tear things down, in local mode."""
    from Cauldron.api import teardown, use
    use("local")
    from Cauldron.DFW import Service
    svc = Service(servicename2, None)
    svc[keyword_name2].modify('10')
    teardown()
    del svc
    
    use("local")
    from Cauldron.DFW import Service
    svc2 = Service(servicename2, None)
    assert svc2[keyword_name2].read() == None