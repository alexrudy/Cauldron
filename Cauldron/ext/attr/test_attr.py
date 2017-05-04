# -*- coding: utf-8 -*-

import pytest

from . import Service, ktl_context

@pytest.fixture
def service(request, dispatcher, keyword_name):
    """A service dispatch tool."""
    mykw = dispatcher[keyword_name]
    return dispatcher

def test_keyword_context(service, client, keyword_name):
    """Test a write method."""
    client[keyword_name].write("20")
    with ktl_context(client, **{keyword_name:"10"}):
        assert client[keyword_name].read() == "10"
        assert client[keyword_name]['ascii'] == "10"
    
    assert client[keyword_name]['ascii'] == "20"
    assert client[keyword_name].read() == "20"
    
def test_service_attr(service, client, keyword_name):
    """Test the service attr object."""
    svc = Service(client)
    setattr(svc, keyword_name, "10")
    assert getattr(svc, keyword_name) == "10"