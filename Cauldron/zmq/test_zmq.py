# -*- coding: utf-8 -*-
"""Tests specific to the ZMQ backend."""

import pytest
import time
import threading

from .broker import ZMQBroker
from .thread import ZMQThread, ZMQThreadError
from ..conftest import fail_if_not_teardown, available_backends
from ..api import use
from ..config import cauldron_configuration, reset_timeouts
from ..types import String

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
    
@pytest.fixture
def config(config):
    """Configuration"""
    reset_timeouts()
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
    
class DummyThread(ZMQThread):
    """A dummy thread, which does nothing, then ends."""
    
    def __init__(self, *args, **kwargs):
        super(DummyThread, self).__init__(*args, **kwargs)
        self.shutdown = threading.Event()
    
    def thread_target(self):
        self.running.set()
        self.started.set()
        self.shutdown.wait()
        

class BadThread(ZMQThread):
    """A misbehaving thread which errors."""
    
    def thread_target(self):
        self.started.set()
        self.running.set()
        raise ValueError("This thread is bad!")


def test_thread_success():
    """Test the ZMQThread apparatus."""
    t = DummyThread("DummyThread")
    assert not t.running.is_set()
    assert not t.started.is_set()
    assert not t.finished.is_set()
    with pytest.raises(ZMQThreadError):
        t.check(timeout=0.1)
    t.start()
    assert not t.finished.is_set()
    t.check(timeout=0.1)
    t.shutdown.set()
    t.finished.wait(0.1)
    assert t.finished.is_set()
    with pytest.raises(ZMQThreadError):
        t.check(timeout=0.1)
    
def test_thread_bad():
    """Test the ZMQThread apparatus."""
    t = BadThread("BadThread")
    assert not t.running.is_set()
    assert not t.started.is_set()
    assert not t.finished.is_set()
    t.start()
    t.finished.wait(0.1)
    with pytest.raises(ZMQThreadError) as excinfo:
        t.check(timeout=0.1)
    assert str(excinfo.value).endswith("from ValueError('This thread is bad!',)")
    assert t.finished.is_set()
    with pytest.raises(ZMQThreadError):
        t.check(timeout=0.1)