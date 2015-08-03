# -*- coding: utf-8 -*-

import time
import pytest

@pytest.fixture
def service(dispatcher):
    """A service dispatch tool."""
    mykw = dispatcher['KEYWORD']
    dispatcher._begin()
    return dispatcher

def test_read_write(service, client):
    """Test a write method."""
    
    client['KEYWORD'].write("10")
    assert client['KEYWORD'].read() == "10"
    
def test_read_write_client(service, client):
    """Test a write/read via the client object."""
    client.write('KEYWORD',"10")
    assert client.read('KEYWORD') == "10"
    
def test_monitored(service, client):
    """Check for clients which broadcast, should be true by default."""
    assert client['KEYWORD']['monitored'] == False
    assert client['KEYWORD']['monitor'] == False
    
def test_has_keyword(service, client):
    """Has keyword."""
    assert client.has_keyword("KEYWORD")
    assert client.has_key("KEYWORD")
    assert "KEYWORD" in client
    assert not client.has_keyword("MISSINGKEYWORD")
    assert not client.has_key("MISSINGKEYWORD")
    assert "MISSINGKEYWORD" not in client
    
def test_missing_keyword(service, client):
    """Test missing keyword."""
    with pytest.raises(KeyError):
        client['MISSINGKEYWORD']
    
def test_populate_keywords(backend, servicename, service):
    """Test populate keywords"""
    from Cauldron import ktl
    client = ktl.Service(servicename, populate=True)
    assert "KEYWORD" in client.populated()
    assert "MISSINGKEYWORD" not in client.populated()
    
def test_populated_keyword(service, client):
    """Test populated"""
    assert client['KEYWORD']['populated'] == False
    client["KEYWORD"].write("10")
    client["KEYWORD"].read()
    assert client['KEYWORD']['populated'] == True
    

def test_clone(service, client):
    """Test the clone."""
    assert client["KEYWORD"].clone().name == "KEYWORD"

def test_timestamp(service, client):
    """Test timestamp"""
    client["KEYWORD"].write("10")
    client["KEYWORD"].read()
    assert isinstance(client['KEYWORD']['timestamp'], float)


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
    