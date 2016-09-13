# -*- coding: utf-8 -*-
"""Tests for the schedule features of keywords."""

import pytest
import time
import functools

# These can be removed once scheduler is supported for all backends.
from ..conftest import fail_if_not_teardown, available_backends
pytestmark = pytest.mark.skipif("zmq" not in available_backends, reason="requires zmq")

@pytest.fixture
def backend(request, config):
    """Always return the zmq backend."""
    from Cauldron.api import use
    use("zmq")
    request.addfinalizer(fail_if_not_teardown)
    from Cauldron.zmq.broker import ZMQBroker
    b = ZMQBroker.setup(config=config, timeout=0.01, daemon=False)
    if b:
        request.addfinalizer(functools.partial(b.stop, timeout=0.1))
    return "zmq"
    
def increment(self):
    """Increment function"""
    value = self.cast(self.value) if self.value is not None else 0
    newvalue = value + 1
    if newvalue > 10:
        raise ValueError()
    self.set(str(newvalue))
    return str(newvalue)

def test_period(dispatcher, client, keyword_name1):
    """Test setting a period for updates from a keyword."""
    
    from Cauldron import DFW
    kw = DFW.Keyword.Integer(keyword_name1, dispatcher)
    kw.update = functools.partial(increment, kw)
    
    value = client[keyword_name1].read(binary=True)
    kw.period(0.1)
    time.sleep(0.3)
    value2 = client[keyword_name1].read(binary=True)
    assert value < value2
    
def test_bad_period(dispatcher, client, keyword_name1):
    """Test a period which should go bad."""
    from Cauldron import DFW
    from ..exc import DispatcherError
    kw = DFW.Keyword.Integer(keyword_name1, dispatcher)
    kw.update = functools.partial(increment, kw)
    
    value = client[keyword_name1].read(binary=True)
    client[keyword_name1].write(10)
    kw.period(0.01)
    time.sleep(0.5)
    with pytest.raises(DispatcherError):
        value2 = client[keyword_name1].read(binary=True)

def test_schedule(dispatcher, client, keyword_name1):
    """Test setting a period for updates from a keyword."""
    
    from Cauldron import DFW
    kw = DFW.Keyword.Integer(keyword_name1, dispatcher)
    kw.update = functools.partial(increment, kw)
    
    value = client[keyword_name1].read(binary=True)
    kw.schedule(time.time() + 0.5)
    time.sleep(1.0)
    value2 = client[keyword_name1].read(binary=True)
    
    appt_time = time.time() + 1.5
    kw.schedule(appt_time)
    kw.schedule(appt_time)
    time.sleep(0.1)
    kw.schedule(appt_time, cancel=True)
    kw.schedule(appt_time, cancel=True)
    
    value2 = client[keyword_name1].read(binary=True)
    
    assert value < value2