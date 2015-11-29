# -*- coding: utf-8 -*-
"""
Tests specific to the local backend.
"""

import pytest
pytestmark = pytest.mark.usefixtures("teardown_cauldron")

from ..conftest import fail_if_not_teardown

@pytest.fixture
def usemock(request):
    """Use the local backend."""
    from Cauldron.api import use
    use('mock')
    request.addfinalizer(fail_if_not_teardown)

@pytest.fixture
def mock_service(usemock, servicename, config):
    """A 'mock' service, which is forgiving."""
    from Cauldron.DFW import Service
    svc = Service(servicename, config=config)
    mykw = svc['KEYWORD']
    return svc
    
@pytest.fixture
def mock_client(servicename):
    """A 'mock' client, which doesn't even require a service backend."""
    from Cauldron import ktl
    return ktl.Service(servicename)

def test_duplicate_services(usemock):
    """Test duplicate 'mock' services."""
    from Cauldron.DFW import Service
    svc = Service("MYSERVICE", config=None)
    with pytest.raises(ValueError):
        svc2 = Service("MYSERVICE", config=None)
    svc3 = Service.get_service("MYSERVICE")
    assert svc3 is svc
    
def test_client_not_started(usemock, servicename):
    """Use mock, don't fail when a client hasn't been started yet."""
    from Cauldron.ktl import Service
    Service(servicename)
    
def test_mock_has_keyword(usemock, mock_client):
    """Mock has a client."""
    assert mock_client.has_keyword("anyvaluewilldo")