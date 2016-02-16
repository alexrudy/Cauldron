# -*- coding: utf-8 -*-

import time
import pytest
import functools
import inspect
import threading

@pytest.fixture
def service(request, dispatcher):
    """A service dispatch tool."""
    mykw = dispatcher['KEYWORD']
    return dispatcher
    
def test_create_and_destroy_client(service):
    """Make a client object."""
    from Cauldron import ktl
    svc = ktl.Service(service.name)
    del svc

def test_read_write(service, client):
    """Test a write method."""
    
    client['KEYWORD'].write("10")
    assert client['KEYWORD'].read() == "10"
    service.shutdown()
    
def test_read_write_client(service, client):
    """Test a write/read via the client object."""
    client.write('KEYWORD',"10")
    assert client.read('KEYWORD') == "10"
    service.shutdown()
    
def test_read_write_asynchronous(service, client):
    """docstring for test_read_write_asynchronous"""
    client.write('KEYWORD',"10", wait=False)
    
def test_monitored(service, client):
    """Check for clients which broadcast, should be true by default."""
    assert client['KEYWORD']['monitored'] == False
    assert client['KEYWORD']['monitor'] == False
    service.shutdown()
    
def test_has_keyword(service, client):
    """Has keyword."""
    assert client.has_keyword("KEYWORD")
    assert client.has_key("KEYWORD")
    assert "KEYWORD" in client
    assert not client.has_keyword("MISSINGKEYWORD")
    assert not client.has_key("MISSINGKEYWORD")
    assert "MISSINGKEYWORD" not in client
    service.shutdown()
    
    
def test_missing_keyword(service, client):
    """Test missing keyword."""
    with pytest.raises(KeyError):
        client['MISSINGKEYWORD']
    service.shutdown()
    
    
def test_populate_keywords(backend, servicename, service):
    """Test populate keywords"""
    from Cauldron import ktl
    client = ktl.Service(servicename, populate=True)
    assert "KEYWORD" in client.populated()
    assert "MISSINGKEYWORD" not in client.populated()
    service.shutdown()
    
    
def test_populated_keyword(service, client):
    """Test populated"""
    assert client['KEYWORD']['populated'] == False
    client["KEYWORD"].write("10")
    client["KEYWORD"].read()
    assert client['KEYWORD']['populated'] == True
    service.shutdown()
    
    

def test_clone(service, client):
    """Test the clone."""
    assert client["KEYWORD"].clone().name == "KEYWORD"
    service.shutdown()
    

def test_timestamp(service, client):
    """Test timestamp"""
    client["KEYWORD"].write("10")
    client["KEYWORD"].read()
    assert isinstance(client['KEYWORD']['timestamp'], float)
    service.shutdown()
    

def test_populated(service, client):
    """Test populated."""
    keyword = client["KEYWORD"]
    assert client.populated() == ["KEYWORD"]
    service.shutdown()
    
    
def test_binary(service, client):
    """Get the binary version of a keyword value."""
    keyword = client["KEYWORD"]
    keyword.write("SomeValue")
    keyword.read()
    assert keyword['binary'] == "SomeValue"
    service.shutdown()
    
    
def test_current_value(service, client):
    """Get the current value."""
    keyword = client["KEYWORD"]
    keyword.write("SomeValue")
    keyword.read()
    assert keyword._current_value() == "SomeValue"
    assert keyword._current_value(both=True) == ("SomeValue", "SomeValue")
    assert keyword._current_value(binary=True) == "SomeValue"
    assert keyword._current_value(both=True, binary=True) == ("SomeValue", "SomeValue")
    service.shutdown()

def test_monitor(service, client, waittime):
    """Test .monitor() for asynchronous broadcast monitoring."""
    
    def monitor(keyword):
        """Monitor"""
        keyword.service.log.log(5, "monitor callback received.")
        monitor.monitored.set()
    
    monitor.monitored = threading.Event()
    
    client["KEYWORD"].callback(monitor)
    client["KEYWORD"].monitor(prime=False)
    monitor.monitored.wait(waittime)
    assert not monitor.monitored.is_set()
    
    service["KEYWORD"].modify("SomeValue")
    monitor.monitored.wait(waittime)
    assert monitor.monitored.is_set()
    
    client["KEYWORD"].callback(monitor, remove=True)
    monitor.monitored.clear()
    service["KEYWORD"].modify("OtherValue")
    monitor.monitored.wait(waittime)
    assert not monitor.monitored.is_set()
    
    monitor.monitored.clear()
    client["KEYWORD"].callback(monitor, preferred=True)
    client["KEYWORD"].monitor(prime=True)
    service["KEYWORD"].modify("SomeValue")
    monitor.monitored.wait(waittime)
    assert monitor.monitored.is_set()
    monitor.monitored.clear()
    
    client["KEYWORD"].monitor(start=False)
    service["KEYWORD"].modify("OtherValue")
    monitor.monitored.wait(waittime)
    assert not monitor.monitored.is_set()
    

def test_subscribe(service, client, waittime):
    """Test .subscribe() which should work like .monitor()"""
    
    def monitor(keyword):
        """Monitor"""
        keyword.service.log.log(5, "monitor callback received.")
        monitor.monitored.set()
    
    monitor.monitored = threading.Event()
    
    client["KEYWORD"].callback(monitor)
    client["KEYWORD"].subscribe(prime=False)
    monitor.monitored.wait(waittime)
    assert not monitor.monitored.is_set()
    service["KEYWORD"].modify("SomeValue")
    monitor.monitored.wait(waittime)
    assert monitor.monitored.is_set()
    
