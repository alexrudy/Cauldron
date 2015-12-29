# -*- coding: utf-8 -*-
import pytest
import time
import threading
from ..conftest import available_backends

pytestmark = pytest.mark.skipif("redis" not in available_backends, reason="requires REDIS")

from ..conftest import fail_if_not_teardown

@pytest.fixture
def useredis(request):
    """Use the local backend."""
    from Cauldron.api import use
    use('redis')

@pytest.fixture
def redis_service(request, useredis, servicename, config):
    """docstring for local_service"""
    from Cauldron.DFW import Service
    svc = Service(servicename, config=config)
    mykw = svc['KEYWORD']
    request.addfinalizer(lambda : svc.shutdown())
    request.addfinalizer(fail_if_not_teardown)
    return svc
    
@pytest.fixture
def redis_client(redis_service, servicename):
    """Test a client."""
    from Cauldron import ktl
    return ktl.Service(servicename)

def test_redis_available():
    """Test that REDIS is or isn't available."""
    from Cauldron.redis.common import REDIS_AVAILALBE, check_redis
    
    r = check_redis()
    REDIS_AVAILALBE.off()
    with pytest.raises(RuntimeError):
        check_redis()
    REDIS_AVAILALBE.on()
    
def test_read_async(redis_service, redis_client):
    """Test reading asynchronously."""
    redis_service["KEYWORD"].modify("MYVALUE")
    
    # Spawn an asynchronous read.
    redis_client['KEYWORD'].read(wait=False)
    
    # Allow background to process.
    time.sleep(0.001)
    assert redis_client["KEYWORD"]['ascii'] == "MYVALUE"

def test_wait(redis_client):
    """Test redis wait()"""
    from Cauldron.exc import CauldronAPINotImplemented
    with pytest.raises(CauldronAPINotImplemented):
        redis_client["KEYWORD"].wait()
        
    
