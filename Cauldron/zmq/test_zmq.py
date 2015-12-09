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
def config_zmq(request):
    """Get the configuration item."""
    config = cauldron_configuration
    config.set("zmq","publish", "7802")
    config.set("zmq","broadcast","7801")
    config.set("zmq","broker","7800")
    return config
    
def test_zmq_available():
    """Test that ZMQ is or isn't available."""
    from Cauldron.zmq.common import ZMQ_AVAILABLE, check_zmq
    
    r = check_zmq()
    orig = ZMQ_AVAILABLE.value
    ZMQ_AVAILABLE.off()
    with pytest.raises(RuntimeError):
        check_zmq()
    ZMQ_AVAILABLE.value = orig

def test_router(zmq, config_zmq):
    """Test the router."""
    broker = ZMQBroker.thread(config_zmq)
    
    from Cauldron import DFW
    svc = DFW.Service("test-router", config=config_zmq)
    
    from Cauldron import ktl
    client = ktl.Service("test-router")
    
    svc.shutdown()
    svc = DFW.Service("test-router", config=config_zmq)
    svc.shutdown()
    
    broker.stop()
    time.sleep(0.1)
    assert not broker.is_alive()
    
def test_setup(zmq, config):
    """Test setup and broadcast functions"""
    from Cauldron import DFW
    
    def setup(service):
        """Setup function."""
        DFW.Keyword.Keyword("KEYWORD", service, initial="SOMEVALUE")
    
    svc = DFW.Service("test-router", config=config, setup=setup)
    svc["KEYWORD"]
    