# -*- coding: utf-8 -*-
"""
Tests specific to the local backend.
"""

import pytest
pytestmark = pytest.mark.usefixtures("teardown_cauldron")

@pytest.fixture
def Service():
    """A local Service class."""
    from Cauldron.api import use
    use("local")
    from Cauldron.DFW import Service
    return Service

def test_duplicate_services(Service):
    """Test duplicate services."""
    svc = Service("MYSERVICE", config=None)
    with pytest.raises(ValueError):
        svc2 = Service("MYSERVICE", config=None)
    svc3 = Service.get("MYSERVICE")
    assert svc3 is svc