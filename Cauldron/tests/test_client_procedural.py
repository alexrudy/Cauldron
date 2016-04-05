# -*- coding: utf-8 -*-

import pytest
import threading
from .test_client import service

def test_read_write(service, servicename, keyword_name):
    """Test a write method."""
    
    from Cauldron.ktl.procedural import read, write
    write(servicename, keyword_name, "10")
    assert read(servicename, keyword_name) == "10"
    
def test_argument_checking(service, servicename, keyword_name):
    """Check argument type checking."""
    from Cauldron.ktl.procedural import read, write
    with pytest.raises(TypeError):
        read(1, "hello")
    with pytest.raises(TypeError):
        read(servicename, 1)
    

def test_monitor(service, waittime, keyword_name, servicename):
    """Test .monitor() for asynchronous broadcast monitoring."""
    
    from Cauldron.ktl.procedural import monitor, callback
    
    def monitor_cb(keyword):
        """Monitor"""
        keyword.service.log.log(5, "monitor callback received.")
        monitor_cb.monitored.set()
    
    monitor_cb.monitored = threading.Event()
    
    callback(servicename, keyword_name, monitor_cb)
    monitor(servicename, keyword_name, prime=False)
    
    monitor_cb.monitored.wait(waittime)
    assert not monitor_cb.monitored.is_set()
    
    service[keyword_name].modify("SomeValue")
    monitor_cb.monitored.wait(waittime)
    assert monitor_cb.monitored.is_set()
    
    callback(servicename, keyword_name, monitor_cb, remove=True)
    monitor_cb.monitored.clear()
    service[keyword_name].modify("OtherValue")
    monitor_cb.monitored.wait(waittime)
    assert not monitor_cb.monitored.is_set()
    
    monitor_cb.monitored.clear()
    callback(servicename, keyword_name, monitor_cb, preferred=True)
    monitor(servicename, keyword_name, prime=True)
    service[keyword_name].modify("SomeValue")
    monitor_cb.monitored.wait(waittime)
    assert monitor_cb.monitored.is_set()
    monitor_cb.monitored.clear()
    
    monitor(servicename, keyword_name, start=False)
    service[keyword_name].modify("OtherValue")
    monitor_cb.monitored.wait(waittime)
    assert not monitor_cb.monitored.is_set()
    