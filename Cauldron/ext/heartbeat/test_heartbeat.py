# -*- coding: utf-8 -*-

import pytest
import threading

@pytest.fixture
def heartbeat_keyword(dispatcher_setup):
    """Make a command-keyword object."""
    from Cauldron.ext.heartbeat import HeartbeatKeyword
    def setup(service):
        kwd = HeartbeatKeyword("HEARTBEAT", service)
    dispatcher_setup.append(setup)
    return "HEARTBEAT"

def test_setup_heartbeat_keyword(heartbeat_keyword, dispatcher, client):
    """Test the setup."""
    from Cauldron.ext.heartbeat import HeartbeatKeyword
    assert not HeartbeatKeyword.KTL_REGISTERED
    assert isinstance(dispatcher[heartbeat_keyword], HeartbeatKeyword)
    assert dispatcher[heartbeat_keyword].KTL_TYPE == 'integer'
    assert client[heartbeat_keyword].KTL_TYPE == 'integer'

def test_update_heartbeat_keyword(heartbeat_keyword, dispatcher, client):
    """Write to a command keyword."""
    value_one = client[heartbeat_keyword].read()
    assert value_one != client[heartbeat_keyword].read()
    

    