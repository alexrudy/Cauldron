# -*- coding: utf-8 -*-
"""Tests specific to the ZMQ backend."""

import pytest
import time

from .router import ZMQRouter, register, lookup, shutdown_router
from ..conftest import fail_if_not_teardown
from ..api import use
from ..config import default_configuration, set_module_configuration

@pytest.fixture
def zmq(request):
    """docstring for backend"""
    use("zmq")
    request.addfinalizer(fail_if_not_teardown)
    return "zmq"
    
@pytest.fixture
def config_zmq(request):
    """Get the configuration item."""
    # from six.moves import configparser
    config = default_configuration()
    config.set("zmq-router","port", "7700")
    config.set("zmq-router","first-port","7710")
    config.set("zmq-router","last-port","7800")
    config.set("zmq-router","allow-spawn","no")
    set_module_configuration(config)
    request.addfinalizer(lambda : set_module_configuration(default_configuration()))
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
    router = ZMQRouter.thread(config_zmq)
    
    from Cauldron import DFW
    svc = DFW.Service("test-router", config=config_zmq)
    
    from Cauldron import ktl
    client = ktl.Service("test-router")
    
    svc.shutdown()
    svc = DFW.Service("test-router", config=config_zmq)
    svc.shutdown()
    
    assert shutdown_router(None, config_zmq)
    time.sleep(0.1)
    assert not router.is_alive()
    
def test_setup(zmq, config):
    """Test setup and broadcast functions"""
    from Cauldron import DFW
    
    def setup(service):
        """Setup function."""
        DFW.Keyword.Keyword("KEYWORD", service, initial="SOMEVALUE")
    
    svc = DFW.Service("test-router", config=config, setup=setup)
    svc["KEYWORD"]
    