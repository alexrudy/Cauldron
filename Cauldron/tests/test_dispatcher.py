# -*- coding: utf-8 -*-
"""
Test dispatcher.
"""
import pytest
import threading
from Cauldron.exc import CauldronAPINotImplemented

@pytest.fixture
def waittime():
    """Event waiting time."""
    return 0.1

def test_callbacks(dispatcher, keyword_name):
    """Test callback propagation."""
    
    class CallbackRecieved(Exception): pass
    
    def cb(kw):
        """Dummy Callback"""
        raise CallbackRecieved()
        
    dispatcher[keyword_name].callback(cb)
    
    with pytest.raises(CallbackRecieved):
        dispatcher[keyword_name].modify('1')
    
    assert not dispatcher[keyword_name]._acting
    dispatcher[keyword_name].callback(cb, remove=True)
    dispatcher[keyword_name].modify('1')
    
def test_callbacks_from_client(dispatcher, client, waittime, keyword_name):
    """Test that when modified from a client, exceptions don't kill the responder thread."""
    from Cauldron.exc import DispatcherError
    
    class CallbackRecieved(Exception): pass
    
    def cb(kw):
        """Dummy Callback"""
        cb.triggered.set()
        raise CallbackRecieved("Notification that {0!r} recieved a callback.".format(kw))
    
    cb.triggered = threading.Event()
    
    dispatcher[keyword_name].callback(cb)
    with pytest.raises(CallbackRecieved):
        dispatcher[keyword_name].modify('1')
        
    cb.triggered.wait(waittime)
    assert cb.triggered.is_set()
    cb.triggered.clear()
    
    with pytest.raises(DispatcherError):
        client[keyword_name].write('2')
    
    cb.triggered.wait(waittime)
    assert cb.triggered.is_set()
    cb.triggered.clear()
    
    with pytest.raises(CallbackRecieved):
        dispatcher[keyword_name].modify('3')
    
    cb.triggered.wait(waittime)
    assert cb.triggered.is_set()
    cb.triggered.clear()
    
    dispatcher[keyword_name].callback(cb, remove=True)
    dispatcher[keyword_name].modify('4')
    
def test_recursive_callbacks(dispatcher, keyword_name):
    """Test a recursive callback function."""
    def cb(keyword):
        cb.count += 1
        keyword.modify("OtherValue")
    
    cb.count = 0
    dispatcher[keyword_name].callback(cb)
    dispatcher[keyword_name].modify("SomeValue")
    assert cb.count == 1
    assert dispatcher[keyword_name].value == "OtherValue"
        
def test_check(dispatcher, client, keyword_name1):
    """Test that check accepts only values of the correct type, etc."""
    class CheckFailed(Exception): pass
    
    def fail_check(value):
        raise CheckFailed
    
    from Cauldron import DFW
    kw = dispatcher[keyword_name1]
    kw.check = fail_check 
    
    with pytest.raises(CheckFailed):
        kw.set("10")
    
    with pytest.raises(CheckFailed):
        kw.modify("10")
    

def test_modfiy(dispatcher, client, keyword_name):
    """Check that a modify happens correctly between a dispatcher and a client."""
    dispatcher[keyword_name].modify("16xTest")
    assert "16xTest" == client[keyword_name].read()
    assert "16xTest" == dispatcher[keyword_name].read()
    
def test_duplicate_keyword(dispatcher, keyword_name):
    """Test creating a duplicate keyword after setup."""
    from Cauldron import DFW
    with pytest.raises(ValueError):
        otherkw = DFW.Keyword.Keyword(keyword_name, dispatcher)
        
def test_contains(dispatcher, missing_keyword_name):
    """Test the 'in' for service"""
    from Cauldron import DFW
    
    assert missing_keyword_name not in dispatcher
    assert missing_keyword_name.lower() not in dispatcher
    DFW.Keyword.Keyword(missing_keyword_name, dispatcher)
    assert missing_keyword_name in dispatcher
    assert missing_keyword_name.lower() in dispatcher
    

def test_keyword_contains(dispatcher, keyword_name):
    """Test the 'in' for keywords"""
    keyword = dispatcher[keyword_name]
    assert "Some" not in keyword
    keyword.modify("SomeValue")
    assert "omeV" in keyword
    assert "Other" not in keyword
    
def test_update_no_value(dispatcher, keyword_name):
    """Test an update with no value."""
    keyword = dispatcher[keyword_name]
    assert keyword.update() is None

@pytest.mark.xfail(raises=CauldronAPINotImplemented)
def test_initialize_with_period(dispatcher_args, dispatcher_setup, keyword_name):
    """Test the dispatcher keyword's period argument."""
    from Cauldron import DFW
    from Cauldron.exc import CauldronAPINotImplemented
    
    def setup(dispatcher):
        DFW.Keyword.Keyword(keyword_name, dispatcher, period=10)
    
    del dispatcher_setup[:]
    dispatcher_setup.append(setup)
    from Cauldron import DFW
    svc = DFW.Service(*dispatcher_args)

@pytest.mark.xfail(raises=CauldronAPINotImplemented)
def test_period(dispatcher, keyword_name):
    """Fail with period tests."""
    from Cauldron.exc import CauldronAPINotImplemented
    dispatcher[keyword_name].period(10)
    
def test_with_non_string(dispatcher, keyword_name):
    """Test with a non-string value."""
    with pytest.raises(TypeError):
        dispatcher[keyword_name].set(10)
    
def test_value(dispatcher, keyword_name):
    """Test the value."""
    assert dispatcher[keyword_name]['value'] is None
    dispatcher[keyword_name].modify("1")
    assert dispatcher[keyword_name]['value'] is not None
    del dispatcher[keyword_name].value
    assert dispatcher[keyword_name]['value'] is None

@pytest.mark.xfail(raises=CauldronAPINotImplemented)
def test_schedule(dispatcher, keyword_name):
    """Test the schedule method."""
    import datetime
    dispatcher[keyword_name].schedule(datetime.datetime.now() + datetime.timedelta(seconds=10))

def test_setup_function(backend, servicename, config, keyword_name):
    """Test a dispatcher setup function."""
    from Cauldron import DFW
    def setup(service):
        """Set up a service"""
        kwd = DFW.Keyword.Keyword(keyword_name, service)
        print("Service setup")
        
    service = DFW.Service(servicename, config, setup=setup)
    print("Service __init__")
    assert keyword_name in service
    print("Service check")
    del service
    print("Service done.")
    
def test_service_setitem(dispatcher, missing_keyword_name):
    """Test a dispatcher service's setitem."""
    from Cauldron import DFW
    with pytest.raises(TypeError):
        dispatcher[missing_keyword_name] = 10
    keyword = DFW.Keyword.Keyword(missing_keyword_name, dispatcher)
    with pytest.raises(ValueError):
        DFW.Keyword.Keyword(missing_keyword_name, dispatcher)
    with pytest.raises(RuntimeError):
        dispatcher[missing_keyword_name] = keyword
    
    with pytest.raises(TypeError):
        dispatcher[missing_keyword_name] = 10

def test_async_read(dispatcher, servicename, keyword_name):
    """Aysnchronous writer"""
    dkwd = dispatcher[keyword_name]
    dkwd.modify('1')
    from Cauldron import ktl
    client = ktl.Service(servicename)
    task = client[keyword_name].read(wait=False)
    client[keyword_name].wait(sequence=task)
    assert client[keyword_name]['ascii'] == '1'
    
def test_async_write(dispatcher, servicename, keyword_name):
    """Aysnchronous writer"""
    dkwd = dispatcher[keyword_name]
    dkwd.modify('1')
    
    from Cauldron import ktl
    client = ktl.Service(servicename)
    task = client[keyword_name].write('2', wait=False)
    client[keyword_name].wait(sequence=task)
    assert dkwd.value == '2'

def test_broadcast(dispatcher, keyword_name):
    """Check that broadcast works."""
    keyword = dispatcher[keyword_name]
    keyword.set("10")
    dispatcher.broadcast()
    
def test_set_statuskeyword(dispatcher, keyword_name, keyword_name1):
    """Check that broadcast works."""
    assert dispatcher.setStatusKeyword(keyword_name)
    assert not dispatcher.setStatusKeyword(keyword_name)
    assert dispatcher.setStatusKeyword(keyword_name1)
    
def test_keyword_list(dispatcher, keyword_name, missing_keyword_name):
    """Check the keyword list."""
    assert keyword_name in dispatcher.keywords()
    dispatcher[missing_keyword_name].modify("10")
    assert missing_keyword_name in dispatcher.keywords()
    

def test_bad_initial_value(backend, servicename, config, keyword_name, keyword_name1):
    """Test a dispatcher setup function."""
    from Cauldron import DFW
    def setup(service):
        """Set up a service"""
        DFW.Keyword.Boolean(keyword_name1, service, initial=100)
        DFW.Keyword.Integer(keyword_name, service, initial=100)
        
    service = DFW.Service(servicename, config, setup=setup)
    try:
        assert keyword_name1 in service
        assert service[keyword_name1]['value'] == None
        assert int(service[keyword_name]['value']) == 100
    finally:
        service.shutdown()
    
def test_write_before_begin(backend, servicename, config, keyword_name):
    """Test a dispatcher setup function."""
    from Cauldron import DFW
    def setup(service):
        """Set up a service"""
        DFW.Keyword.Integer(keyword_name, service, initial=5)
        service[keyword_name].modify(str(10))
        
    service = DFW.Service(servicename, config, setup=setup)
    assert keyword_name in service
    assert service[keyword_name]['value'] == str(10)


def test_getitem_interface(dispatcher, keyword_name):
    """Test the getitem interface to dispatcher keywords."""
    keyword = dispatcher[keyword_name]
    keyword.modify("SomeValue")
    
    assert keyword['value'] == "SomeValue"
    assert keyword['name'] == keyword_name
    assert keyword['readonly'] == False
    assert keyword['writeonly'] == False
    
    with pytest.raises(KeyError):
        keyword['some-other-key']
    with pytest.raises(KeyError):
        keyword[1]
    
def test_keyword_fullname(dispatcher, keyword_name):
    """Test a keyword fullname."""
    keyword = dispatcher[keyword_name]
    assert keyword.full_name == "{0}.{1}".format(dispatcher.name, keyword_name)
    
def test_strict_xml(backend, servicename, xmlvar):
    """Test the XML validation in strict mode."""
    from Cauldron.api import use_strict_xml
    use_strict_xml()
    from Cauldron.DFW import Service
    svc = Service(servicename, None)
