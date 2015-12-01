# -*- coding: utf-8 -*-
"""
Test dispatcher.
"""
import pytest
import threading

pytestmark = pytest.mark.usefixtures("teardown_cauldron")

@pytest.fixture
def waittime():
    """Event waiting time."""
    return 0.1

def test_callbacks(dispatcher):
    """Test callback propagation."""
    
    class CallbackRecieved(Exception): pass
    
    def cb(kw):
        """Dummy Callback"""
        raise CallbackRecieved()
        
    dispatcher['MODE'].callback(cb)
    
    with pytest.raises(CallbackRecieved):
        dispatcher['MODE'].modify('1')
    
    assert not dispatcher['MODE']._acting
    dispatcher['MODE'].callback(cb, remove=True)
    dispatcher['MODE'].modify('1')
    
def test_callbacks_from_client(dispatcher, client, waittime):
    """Test that when modified from a client, exceptions don't kill the responder thread."""
    from Cauldron.exc import DispatcherError
    
    class CallbackRecieved(Exception): pass
    
    def cb(kw):
        """Dummy Callback"""
        cb.triggered.set()
        raise CallbackRecieved("Notification that {0!r} recieved a callback.".format(kw))
    
    cb.triggered = threading.Event()
    
    dispatcher['MODE'].callback(cb)
    with pytest.raises(CallbackRecieved):
        dispatcher['MODE'].modify('1')
        
    cb.triggered.wait(waittime)
    assert cb.triggered.is_set()
    cb.triggered.clear()
    
    with pytest.raises(DispatcherError):
        client['MODE'].write('2', timeout=1)
    
    cb.triggered.wait(waittime)
    assert cb.triggered.is_set()
    cb.triggered.clear()
    
    with pytest.raises(CallbackRecieved):
        dispatcher['MODE'].modify('3')
    
    cb.triggered.wait(waittime)
    assert cb.triggered.is_set()
    cb.triggered.clear()
    
    dispatcher['MODE'].callback(cb, remove=True)
    dispatcher['MODE'].modify('4')
    
def test_recursive_callbacks(dispatcher):
    """Test a recursive callback function."""
    def cb(keyword):
        cb.count += 1
        keyword.modify("OtherValue")
    
    cb.count = 0
    dispatcher["KEYWORD"].callback(cb)
    dispatcher["KEYWORD"].modify("SomeValue")
    assert cb.count == 2
    assert dispatcher["KEYWORD"].value == "OtherValue"
        
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
    

def test_keyword_contains(dispatcher):
    """Test the 'in' for keywords"""
    keyword = dispatcher['KEYWORD']
    assert "Some" not in keyword
    keyword.modify("SomeValue")
    assert "omeV" in keyword
    assert "Other" not in keyword
    
def test_update_no_value(dispatcher):
    """Test an update with no value."""
    keyword = dispatcher['KEYWORD']
    assert keyword.update() is None

@pytest.mark.xfail
def test_initialize_with_period(dispatcher):
    """Test the dispatcher keyword's period argument."""
    from Cauldron import DFW
    DFW.Keyword.Keyword("keyword", dispatcher, period=10)

@pytest.mark.xfail
def test_period(dispatcher):
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
        kwd = DFW.Keyword.Keyword("KEYWORD", service)
        print("Service setup")
        
    service = DFW.Service(servicename, config, setup=setup)
    print("Service __init__")
    assert "KEYWORD" in service
    print("Service check")
    del service
    print("Service done.")
    
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
    
def test_set_statuskeyword(dispatcher):
    """Check that broadcast works."""
    assert dispatcher.setStatusKeyword('KEYWORD')
    assert not dispatcher.setStatusKeyword('KEYWORD')
    assert dispatcher.setStatusKeyword('OTHERKEYWORD')
    
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

def test_teardown(servicename, teardown_cauldron):
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
    
def test_getitem_interface(dispatcher):
    """Test the getitem interface to dispatcher keywords."""
    keyword = dispatcher['MYKEYWORD']
    keyword.modify("SomeValue")
    
    assert keyword['value'] == "SomeValue"
    assert keyword['name'] == "MYKEYWORD"
    assert keyword['readonly'] == False
    assert keyword['writeonly'] == False
    
    with pytest.raises(KeyError):
        keyword['some-other-key']
    with pytest.raises(KeyError):
        keyword[1]
    
def test_keyword_fullname(dispatcher):
    """Test a keyword fullname."""
    keyword = dispatcher['MYKEYWORD']
    assert keyword.full_name == "{0}.MYKEYWORD".format(dispatcher.name)
    
def test_strict_xml(backend, servicename, xmlvar):
    """Test the XML validation in strict mode."""
    from Cauldron.api import use_strict_xml
    use_strict_xml()
    from Cauldron.DFW import Service
    svc = Service(servicename, None)
