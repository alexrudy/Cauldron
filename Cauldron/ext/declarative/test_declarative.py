# -*- coding: utf-8 -*-

import pytest

from .descriptor import KeywordDescriptor, DescriptorBase, ServiceNotBound
from .events import _KeywordEvent

@pytest.fixture
def cls():
    """Descriptor test class, defined at runtime to prevent import problems."""
    
    class DescriptorTestClass(DescriptorBase):
        mykeyword = KeywordDescriptor("MYKEYWORD")
        
        def __init__(self):
            super(DescriptorTestClass, self).__init__()
            self.called = set()
    
        @mykeyword.callback
        def callback(self, keyword):
            """Changed value callback"""
            print("Calling 'callback'")
            self.called.add("callback")
        
        @mykeyword.prewrite
        def prewrite(self, keyword, value):
            """Pre-write listener."""
            print("Calling 'prewrite'")
            self.called.add("prewrite")
        
        @mykeyword.preread
        def preread(self, keyword):
            """Pre-read listener."""
            print("Calling 'preread'")
            self.called.add("preread")
            
    return DescriptorTestClass

def test_descriptor_basics(dispatcher, cls):
    """Test basic features of the descriptor protocol"""
    
    instance = cls()
    newinstance = cls()    
    
    print("Starting bind.")
    instance.bind(dispatcher)
    print("Bind done.")
    
    instance.mykeyword = "Hello"
    
    assert len(newinstance.called) == 0
    assert len(cls.mykeyword.callback.callbacks) == 1
    
    cb_name = [ cb.__name__ for cb in cls.mykeyword.callback.callbacks ][0]
    assert cb_name == "callback"
    
    assert cls.mykeyword.keyword == dispatcher["MYKEYWORD"]
    
    assert "callback" in instance.called
    assert "prewrite" in instance.called
    assert "preread" not in instance.called
    assert dispatcher["MYKEYWORD"]["value"] == "Hello"
    assert "preread" not in instance.called
    
    value = instance.mykeyword
    assert "preread" in instance.called
    
    del instance
    
    assert len(cls.mykeyword.callback.callbacks) == 1
    assert newinstance.mykeyword == "Hello"
    
    newinstance.mykeyword = "Goodbye"
    
def test_bind(dispatcher, cls):
    """Test the bind method"""
    
    instance = cls()
    with pytest.raises(ServiceNotBound):
        instance.bind()
        
    instance.bind(dispatcher)
    
    instance.bind()
