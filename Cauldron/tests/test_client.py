# -*- coding: utf-8 -*-

import time
import pytest
import functools
import inspect
import threading

@pytest.fixture
def service(request, dispatcher, keyword_name):
    """A service dispatch tool."""
    mykw = dispatcher[keyword_name]
    return dispatcher
    
def test_create_and_destroy_client(service):
    """Make a client object."""
    from Cauldron import ktl
    svc = ktl.Service(service.name)
    del svc

def test_read_write(service, client, keyword_name):
    """Test a write method."""
    
    client[keyword_name].write("10")
    assert client[keyword_name]['ascii'] == "10"
    assert client[keyword_name].read() == "10"
    
def test_read_write_client(service, client, keyword_name):
    """Test a write/read via the client object."""
    client.write(keyword_name,"10")
    assert client.read(keyword_name) == "10"
    
def test_read_write_asynchronous(service, client, keyword_name, waittime):
    """Test the the client can write in an asynchronous fashion."""
    keyword = client[keyword_name]
    sequence = keyword.write("10", wait=False)
    keyword.wait(sequence=sequence, timeout=waittime)
    
    
def test_monitored(service, client, keyword_name):
    """Check for clients which broadcast, should be true by default."""
    assert client[keyword_name]['monitored'] == False
    assert client[keyword_name]['monitor'] == False
    
def test_has_keyword(service, client, keyword_name, missing_keyword_name):
    """Has keyword."""
    assert client.has_keyword(keyword_name)
    assert client.has_key(keyword_name)
    assert keyword_name in client
    assert not client.has_keyword(missing_keyword_name)
    assert not client.has_key(missing_keyword_name)
    assert missing_keyword_name not in client
    
    
def test_missing_keyword(service, client, missing_keyword_name):
    """Test missing keyword."""
    with pytest.raises(KeyError):
        client[missing_keyword_name]
    
    
def test_populate_keywords(backend, servicename, service, keyword_name, missing_keyword_name):
    """Test populate keywords"""
    from Cauldron import ktl
    client = ktl.Service(servicename, populate=True)
    assert keyword_name in client.populated()
    assert missing_keyword_name not in client.populated()
    
    
def test_populated_keyword(service, client, keyword_name):
    """Test populated"""
    assert client[keyword_name]['populated'] == False
    client[keyword_name].write("10")
    client[keyword_name].read()
    assert client[keyword_name]['populated'] == True

def test_clone(service, client, keyword_name):
    """Test the clone."""
    assert client[keyword_name].clone().name == keyword_name

def test_timestamp(service, client, keyword_name):
    """Test timestamp"""
    client[keyword_name].write("10")
    client[keyword_name].read()
    assert isinstance(client[keyword_name]['timestamp'], float)    

def test_populated(service, client, keyword_name):
    """Test populated."""
    keyword = client[keyword_name]
    assert client.populated() == [keyword_name]
    
def test_binary(service, client, keyword_name):
    """Get the binary version of a keyword value."""
    keyword = client[keyword_name]
    keyword.write("SomeValue")
    keyword.read()
    assert keyword['binary'] == "SomeValue"
    
def test_current_value(service, client, keyword_name):
    """Get the current value."""
    keyword = client[keyword_name]
    keyword.write("SomeValue")
    keyword.read()
    assert keyword._current_value() == "SomeValue"
    assert keyword._current_value(both=True) == ("SomeValue", "SomeValue")
    assert keyword._current_value(binary=True) == "SomeValue"
    assert keyword._current_value(both=True, binary=True) == ("SomeValue", "SomeValue")

def test_monitor(service, client, waittime, keyword_name):
    """Test .monitor() for asynchronous broadcast monitoring."""
    
    def monitor(keyword):
        """Monitor"""
        keyword.service.log.log(5, "monitor callback received.")
        monitor.monitored.set()
    
    monitor.monitored = threading.Event()
    
    client[keyword_name].callback(monitor)
    client[keyword_name].monitor(prime=False)
    monitor.monitored.wait(waittime)
    assert not monitor.monitored.is_set()
    
    service[keyword_name].modify("SomeValue")
    monitor.monitored.wait(waittime)
    assert monitor.monitored.is_set()
    
    client[keyword_name].callback(monitor, remove=True)
    monitor.monitored.clear()
    service[keyword_name].modify("OtherValue")
    monitor.monitored.wait(waittime)
    assert not monitor.monitored.is_set()
    
    monitor.monitored.clear()
    client[keyword_name].callback(monitor, preferred=True)
    client[keyword_name].monitor(prime=True)
    service[keyword_name].modify("SomeValue")
    monitor.monitored.wait(waittime)
    assert monitor.monitored.is_set()
    monitor.monitored.clear()
    
    client[keyword_name].monitor(start=False)
    service[keyword_name].modify("OtherValue")
    monitor.monitored.wait(waittime)
    assert not monitor.monitored.is_set()
    

def test_subscribe(service, client, waittime, keyword_name):
    """Test .subscribe() which should work like .monitor()"""
    
    def monitor(keyword):
        """Monitor"""
        keyword.service.log.log(5, "monitor callback received.")
        monitor.monitored.set()
    
    monitor.monitored = threading.Event()
    
    client[keyword_name].callback(monitor)
    client[keyword_name].subscribe(prime=False)
    monitor.monitored.wait(waittime)
    assert not monitor.monitored.is_set()
    service[keyword_name].modify("SomeValue")
    monitor.monitored.wait(waittime)
    assert monitor.monitored.is_set()
    
