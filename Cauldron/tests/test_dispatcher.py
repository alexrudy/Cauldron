# -*- coding: utf-8 -*-
"""
Test clients.
"""
import pytest

def test_callbacks(dispatcher, client):
    """Test callback propogation."""
    
    class CallbackRecieved(Exception): pass
    
    def cb(kw):
        """Dummy Callback"""
        raise CallbackRecieved()
        
    dispatcher['MODE'].callback(cb)
    
    with pytest.raises(CallbackRecieved):
        client['MODE'].write('1')
        
    dispatcher['MODE'].callback(cb, remove=True)
    client['MODE'].write('1')
        
def test_check(dispatcher, client):
    """Test that check accepts only values of the correct type, etc."""
    class CheckFailed(Exception): pass
    
    def fail_check(value):
        raise CheckFailed
    
    from Cauldron import DFW
    kw = DFW.Keyword.Keyword("TYPEDKW", dispatcher)
    kw.check = fail_check 
    
    with pytest.raises(CheckFailed):
        kw.set("10")
    
    with pytest.raises(CheckFailed):
        kw.modify("10")
    

def test_modfiy(dispatcher, client):
    """Check that a modify happens correctly between a dispatcher and a client."""
    dispatcher['MODE'].modify("16xTest")
    assert "16xTest" == client['MODE'].read()
    assert "16xTest" == dispatcher['MODE'].read()
    
def test_duplicate_keyword(dispatcher):
    """Test creating a duplicate keyword"""
    from Cauldron import DFW
    DFW.Keyword.Keyword("KEYWORD", dispatcher)
    
    with pytest.raises(ValueError):
        otherkw = DFW.Keyword.Keyword("KEYWORD", dispatcher)
        
def test_contains(dispatcher):
    """Test the 'in' for service"""
    from Cauldron import DFW
    
    assert "KEYWORD" not in dispatcher
    assert "keyword" not in dispatcher
    DFW.Keyword.Keyword("KEYWORD", dispatcher)
    assert "KEYWORD" in dispatcher
    assert "keyword" in dispatcher
    

@pytest.mark.xfail
def test_initialize_with_period(dispatcher):
    """Test the dispatcher keyword's period argument."""
    DFW.Keyword.Keyword("keyword", dispatcher, period=10)

@pytest.mark.xfail
def test_period(dispatcher, client):
    """Fail with period tests."""
    dispatcher["KEYWORD"].period(10)
    
def test_with_non_string(dispatcher):
    """Test with a non-string value."""
    with pytest.raises(TypeError):
        dispatcher['KEYWORD'].set(10)
    
def test_value(dispatcher):
    """Test the value."""
    assert dispatcher['KEYWORD']['value'] is None
    dispatcher['KEYWORD'].modify("1")
    assert dispatcher["KEYWORD"]['value'] is not None
    del dispatcher['KEYWORD'].value
    assert dispatcher['KEYWORD']['value'] is None

@pytest.mark.xfail
def test_schedule(dispatcher):
    """Test the schedule method."""
    import datetime
    dispatcher['KEYWORD'].schedule(datetime.datetime.now() + datetime.timedelta(seconds=10))

def test_setup_function(backend, servicename, config):
    """Test a dispatcher setup function."""
    from Cauldron import DFW
    def setup(service):
        """Set up a service"""
        DFW.Keyword.Keyword("KEYWORD", service)
        
    service = DFW.Service(servicename, config, setup=setup)
    assert "KEYWORD" in service
    
def test_service_setitem(dispatcher):
    """Test a dispatcher service's setitem."""
    from Cauldron import DFW
    keyword = DFW.Keyword.Keyword("KEYWORD", dispatcher)
    with pytest.raises(ValueError):
        DFW.Keyword.Keyword("KEYWORD", dispatcher)
    with pytest.raises(RuntimeError):
        dispatcher['KEYWORD'] = keyword
    
    with pytest.raises(TypeError):
        dispatcher['KEYWORD'] = 10
    with pytest.raises(TypeError):
        dispatcher['OKEYWORD'] = 10

def test_broadcast(dispatcher):
    """Check that broadcast works."""
    keyword = dispatcher['KEYWORD']
    keyword.set("10")
    dispatcher.broadcast()
    
def test_keyword_list(dispatcher):
    """Check the keyword list."""
    assert dispatcher.keywords() == []
    dispatcher['KEYWORD'].modify("10")
    assert dispatcher.keywords() == ['KEYWORD']
    

def test_bad_initial_value(backend, servicename, config):
    """Test a dispatcher setup function."""
    from Cauldron import DFW
    def setup(service):
        """Set up a service"""
        DFW.Keyword.Boolean("BADKEYWORD", service, initial=100)
        DFW.Keyword.Integer("KEYWORD", service, initial=100)
        
    service = DFW.Service(servicename, config, setup=setup)
    assert "BADKEYWORD" in service
    assert service['BADKEYWORD']['value'] == None
    assert int(service['KEYWORD']['value']) == 100
    
def test_write_before_begin(backend, servicename, config):
    """Test a dispatcher setup function."""
    from Cauldron import DFW
    def setup(service):
        """Set up a service"""
        DFW.Keyword.Integer("KEYWORD", service, initial=5)
        service['KEYWORD'].modify(str(10))
        
    service = DFW.Service(servicename, config, setup=setup)
    assert "KEYWORD" in service
    assert service['KEYWORD']['value'] == str(10)

def test_teardown(servicename):
    """Check that teardown really does tear things down, in local mode."""
    from Cauldron.api import teardown, use
    use("local")
    from Cauldron.DFW import Service
    svc = Service(servicename+"2", None)
    svc['MYKEYWORD'].modify('10')
    teardown()
    del svc
    
    use("local")
    from Cauldron.DFW import Service
    svc2 = Service(servicename+"2", None)
    assert svc2['MYKEYWORD'].read() == None
    
