# -*- coding: utf-8 -*-
"""
Test clients.
"""
import pytest

from Cauldron.api import _teardown

def test_callbacks(dispatcher, client):
    """Test callback propogation."""
    
    class CallbackRecieved(Exception): pass
    
    def cb(kw):
        """Dummy Callback"""
        raise CallbackRecieved()
        
    dispatcher['MODE'].callback(cb)
    
    with pytest.raises(CallbackRecieved):
        client['MODE'].write('1')
        
def test_check(dispatcher, client):
    """Test that check accepts only values of the correct type, etc."""
    class CheckFailed(Exception): pass
    
    def fail_check(value):
        raise CheckFailed
    
    from Cauldron import DFW
    kw = dispatcher['TYPEDKW'] = DFW.Keyword("TYPEDKW", dispatcher)
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
    

@pytest.mark.xfail
def test_period(dispatcher, client):
    """Fail with period tests."""
    dispatcher["MODE"].period(10)
    

    
