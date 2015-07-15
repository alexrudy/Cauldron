# -*- coding: utf-8 -*-

import pytest

from .descriptor import KeywordDescriptor, DescriptorBase

@pytest.fixture
def cls():
    """Descriptor test class, defined at runtime to prevent import problems."""
    
    class DescriptorTestClass(DescriptorBase):
        mykeyword = KeywordDescriptor("MYKEYWORD")
        called = set()
    
        @mykeyword.callback
        def callback(self, keyword):
            """Changed value callback"""
            self.called.add("callback")
        
        @mykeyword.prewrite
        def prewrite(self, keyword, value):
            """Pre-write listener."""
            self.called.add("prewrite")
        
        @mykeyword.preread
        def preread(self, keyword):
            """Pre-read listener."""
            self.called.add("preread")
            
    return DescriptorTestClass

def test_descriptor_basics(dispatcher, cls):
    """Test basic features of the descriptor protocol"""
    
    instance = cls()
    
    instance.bind(dispatcher)
    
    instance.mykeyword = "Hello"
    
    assert len(cls.mykeyword.callback.callbacks) == 1
    
    cb_name = [ cb.__name__ for cb in cls.mykeyword.callback.callbacks ][0]
    assert cb_name == "callback"
    
    assert len(cls.mykeyword.callback.listeners) == 1
    listener = cls.mykeyword.callback.listeners[instance]
    assert listener.func
    
    
    assert "callback" in instance.called
    assert "prewrite" in instance.called
    assert "preread" not in instance.called
    assert dispatcher["MYKEYWORD"]["value"] == "Hello"
    assert "preread" not in instance.called
    
    value = instance.mykeyword
    assert "preread" in instance.called
    
    del instance
    
    assert len(cls.mykeyword.callback.callbacks) == 1
    assert len(cls.mykeyword.callback.listeners) == 0
    
