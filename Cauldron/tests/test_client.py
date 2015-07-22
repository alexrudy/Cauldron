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


