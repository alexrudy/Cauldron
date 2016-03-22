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
def zmq(request):
    """docstring for backend"""
    use("zmq")
    request.addfinalizer(fail_if_not_teardown)
    return "zmq"

@pytest.fixture
def broker(request, zmq, config):
    """A zmq broker"""
    broker = ZMQBroker.thread(config)
    request.addfinalizer(broker.stop)
    return broker
    
def test_zmq_available():
    """Test that ZMQ is or isn't available."""
    from Cauldron.zmq.common import ZMQ_AVAILABLE, check_zmq
    
    r = check_zmq()
    orig = ZMQ_AVAILABLE.value
    ZMQ_AVAILABLE.off()
    with pytest.raises(RuntimeError):
        check_zmq()
    ZMQ_AVAILABLE.value = orig

def test_broker(broker, zmq, config):
    """Test the router."""
    from Cauldron import DFW
    svc = DFW.Service("test-router", config=config)
    
    from Cauldron import ktl
    client = ktl.Service("test-router")
    
    svc.shutdown()
    svc = DFW.Service("test-router", config=config)
    svc.shutdown()
    
    
def test_setup(broker, zmq, config):
    """Test setup and broadcast functions"""
    from Cauldron import DFW
    
    def setup(service):
        """Setup function."""
        DFW.Keyword.Keyword("KEYWORD", service, initial="SOMEVALUE")
    
    svc = DFW.Service("test-router", config=config, setup=setup)
    svc["KEYWORD"]
    