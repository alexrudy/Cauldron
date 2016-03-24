# -*- coding: utf-8 -*-
"""Tests specific to the ZMQ backend."""

import pytest
import time

from .broker import ZMQBroker
from ..conftest import fail_if_not_teardown, available_backends
from ..api import use
from ..config import cauldron_configuration

pytestmark = pytest.mark.skipif("zmq" not in available_backends, reason="requires zmq")

@pytest.fixture
def backend(request):
    """Always return the zmq backend."""
    from Cauldron.api import use, teardown, CAULDRON_SETUP
    use("zmq")
    request.addfinalizer(fail_if_not_teardown)
    return "zmq"

@pytest.fixture
def broker(request, backend, config):
    """A zmq broker"""
    b = ZMQBroker.setup(config=config, timeout=0.01)
    if b:
        request.addfinalizer(b.stop)
    return b
    
def test_zmq_available():
    """Test that ZMQ is or isn't available."""
    from Cauldron.zmq.common import ZMQ_AVAILABLE, check_zmq
    
    r = check_zmq()
    orig = ZMQ_AVAILABLE.value
    ZMQ_AVAILABLE.off()
    with pytest.raises(RuntimeError):
        check_zmq()
    ZMQ_AVAILABLE.value = orig

def test_broker(broker, backend, config, servicename):
    """Test the router."""
    from Cauldron import DFW
    svc = DFW.Service(servicename, config=config)
    
    from Cauldron import ktl
    client = ktl.Service(servicename)
    
    svc.shutdown()
    svc = DFW.Service(servicename, config=config)
    svc.shutdown()
    
def test_setup(broker, backend, config, servicename):
    """Test setup and broadcast functions"""
    from Cauldron import DFW
    
    def setup(service):
        """Setup function."""
        DFW.Keyword.Keyword("KEYWORD", service, initial="SOMEVALUE")
    
    svc = DFW.Service(servicename, config=config, setup=setup)
    svc["KEYWORD"]
    
def test_async_read(broker, backend, dispatcher, servicename):
    """Aysnchronous writer"""
    dkwd = dispatcher["KEYWORD"]
    dkwd.modify('1')
    from Cauldron import ktl
    client = ktl.Service(servicename)
    task = client["KEYWORD"].read(wait=False)
    assert task.get(timeout=0.1) == '1'
    
def test_async_write(broker, backend, dispatcher, servicename):
    """Aysnchronous writer"""
    dkwd = dispatcher["KEYWORD"]
    dkwd.modify('1')
    
    from Cauldron import ktl
    client = ktl.Service(servicename)
    task = client["KEYWORD"].write('2', wait=False)
    task.get(timeout=0.1)
    assert dkwd.value == '2'