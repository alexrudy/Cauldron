# -*- coding: utf-8 -*-

import time
import pytest

@pytest.fixture
def service(dispatcher):
    """A service dispatch tool."""
    mykw = dispatcher['KEYWORD']
    dispatcher._begin()
    

def test_read_write(service, client):
    """Test a write method."""
    
    client['KEYWORD'].write("10")
    assert client['KEYWORD'].read() == "10"
    
def test_monitored(service, client):
    """Check for clients which broadcast, should be true by default."""
    assert client['KEYWORD']['monitored'] == False
    assert client['KEYWORD']['monitor'] == False
    
    
def test_populated(service, client):
    """Test populated"""
    assert client['KEYWORD']['populated'] == False
    
def test_clone(service, client):
    """Test the clone."""
    assert client["KEYWORD"].clone().name == "KEYWORD"


def test_monitor(service, client):
    """Test monitoring"""
    
    def monitor(keyword):
        """Monitor"""
        monitor.monitored = True
        print("Monitored!")
    
    monitor.monitored = False
    
    client["KEYWORD"].callback(monitor)
    client["KEYWORD"].monitor(prime=False)
    assert len(client['KEYWORD']._callbacks) == 1
    assert not monitor.monitored
    assert len(service["KEYWORD"]._consumers) == 1
    service["KEYWORD"].modify("SomeValue")
    assert monitor.monitored
    client["KEYWORD"].callback(monitor, remove=True)
    assert len(client['KEYWORD']._callbacks) == 0
    client["KEYWORD"].callback(monitor, preferred=True)
    
def test_subscribe(service, client):
    """Test monitoring"""
    
    def monitor(keyword):
        """Monitor"""
        monitor.monitored = True
        print("Monitored!")
    
    monitor.monitored = False
    
    client["KEYWORD"].callback(monitor)
    client["KEYWORD"].subscribe(prime=False)
    assert len(client['KEYWORD']._callbacks) == 1
    assert not monitor.monitored
    assert len(service["KEYWORD"]._consumers) == 1
    service["KEYWORD"].modify("SomeValue")
    assert monitor.monitored
    
def test_populated(service, client):
    """Test populated."""
    keyword = client["KEYWORD"]
    assert client.populated() == ["KEYWORD"]
    
def test_binary(service, client):
    """Get the binary version of a keyword value."""
    keyword = client["KEYWORD"]
    keyword.write("SomeValue")
    assert keyword['binary'] == "SomeValue"
    
def test_current_value(service, client):
    """Get the current value."""
    keyword = client["KEYWORD"]
    keyword.write("SomeValue")
    keyword.read()
    assert keyword._current_value() == "SomeValue"
    assert keyword._current_value(both=True) == ("SomeValue", "SomeValue")
    assert keyword._current_value(binary=True) == "SomeValue"
    assert keyword._current_value(both=True, binary=True) == ("SomeValue", "SomeValue")
    