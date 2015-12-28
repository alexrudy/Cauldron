# -*- coding: utf-8 -*-

import pytest
import threading

@pytest.fixture
def command_keyword(dispatcher):
    """Make a command-keyword object."""
    from Cauldron.DFW import Keyword
    return Keyword.CommandKeyword("COMMAND", dispatcher)

def test_write_command_keyword(dispatcher, client, command_keyword):
    """Write to a command keyword."""
    command_keyword.modify('1')
    assert client[command_keyword.name].read() == '0'
    
def test_callback(dispatcher, client, command_keyword, waittime):
    """Attach a callback to command keywords."""
    
    name = command_keyword.name
    from Cauldron.exc import DispatcherError
    
    print(command_keyword)
    
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
    
    