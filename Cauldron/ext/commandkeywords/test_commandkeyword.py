# -*- coding: utf-8 -*-

import pytest
import threading

@pytest.fixture
def command_keyword(dispatcher_setup):
    """Make a command-keyword object."""
    from Cauldron.ext.commandkeywords import CommandKeyword
    def setup(service):
        kwd = CommandKeyword("COMMAND", service)
    dispatcher_setup.append(setup)
    return "COMMAND"

def test_setup_command_keyword(command_keyword, dispatcher, client):
    """Test the setup."""
    from Cauldron.ext.commandkeywords import CommandKeyword
    assert not CommandKeyword.KTL_REGISTERED
    assert isinstance(dispatcher[command_keyword], CommandKeyword)
    assert dispatcher[command_keyword].KTL_TYPE == 'boolean'
    assert client[command_keyword].KTL_TYPE == 'boolean'

def test_write_command_keyword(command_keyword, dispatcher, client):
    """Write to a command keyword."""
    dispatcher[command_keyword].modify('1')
    assert client[command_keyword].read() == '0'
    
def test_callback(command_keyword, dispatcher, client, waittime):
    """Attach a callback to command keywords."""
    
    name = dispatcher[command_keyword].name
    from Cauldron.exc import DispatcherError
    
    print(dispatcher[command_keyword])
    
    class CallbackRecieved(Exception): pass
    
    def cb(kw):
        """Dummy Callback"""
        dispatcher.log.debug("Callback Operating...")
        cb.triggered.set()
        raise CallbackRecieved("Notification that {0!r} recieved a callback.".format(kw))
    
    cb.triggered = threading.Event()
    
    dispatcher[name].callback(cb)
    with pytest.raises(CallbackRecieved):
        dispatcher[name].modify('1')
    
    cb.triggered.wait(waittime)
    assert cb.triggered.is_set()
    cb.triggered.clear()
    
    with pytest.raises(DispatcherError):
        client[name].write('1')
    
    cb.triggered.wait(waittime)
    assert cb.triggered.is_set()
    cb.triggered.clear()
    
    dispatcher[name].modify('0')
    cb.triggered.wait(waittime)
    assert not cb.triggered.is_set()
    cb.triggered.clear()
    
    dispatcher.log.debug("Client 0 write...")
    client[name].write('0')
    cb.triggered.wait(waittime)
    assert not cb.triggered.is_set()
    cb.triggered.clear()
    
    dispatcher[name].callback(cb, remove=True)
    dispatcher[name].modify('1')
    
    cb.triggered.wait(waittime)
    assert not cb.triggered.is_set()
    cb.triggered.clear()
    
    