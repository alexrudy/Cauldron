# -*- coding: utf-8 -*-
"""
Tests specific to the local backend.
"""

import pytest
pytestmark = pytest.mark.usefixtures("teardown_cauldron")

from ..conftest import fail_if_not_teardown

@pytest.fixture
def backend(request):
    """Use the local backend."""
    from Cauldron.api import use
    use('mock')
    request.addfinalizer(fail_if_not_teardown)

@pytest.fixture
def mock_service(backend, servicename, config, keyword_name):
    """A 'mock' service, which is forgiving."""
    from Cauldron.DFW import Service
    svc = Service(servicename, config=config)
    mykw = svc[keyword_name]
    return svc
    
@pytest.fixture
def mock_client(servicename):
    """A 'mock' client, which doesn't even require a service backend."""
    from Cauldron import ktl
    return ktl.Service(servicename)

def test_duplicate_services(backend, servicename):
    """Test duplicate 'mock' services."""
    from Cauldron.DFW import Service
    svc = Service(servicename, config=None)
    with pytest.raises(ValueError):
        svc2 = Service(servicename, config=None)
    svc3 = Service.get_service(servicename)
    assert svc3 is svc
    
def test_client_not_started(backend, servicename):
    """Use mock, don't fail when a client hasn't been started yet."""
    from Cauldron.ktl import Service
    Service(servicename)
    
def test_mock_has_keyword(backend, mock_client):
    """Mock has a client."""
    assert mock_client.has_keyword("anyvaluewilldo")