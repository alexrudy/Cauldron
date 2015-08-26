# -*- coding: utf-8 -*-

import pytest

from .descriptor import KeywordDescriptor, DescriptorBase, ServiceNotBound, IntegrityError, ServiceAlreadyBound
from .events import _KeywordEvent

@pytest.fixture
def cls():
    """Descriptor test class, defined at runtime to prevent import problems."""
    
    class DescriptorTestClass(DescriptorBase):
        mykeyword = KeywordDescriptor("MYKEYWORD", initial="SomeValue")
        typedkeyword = KeywordDescriptor("TYPEDKEYWORD", type=int, initial=10)
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
    instance.bind()
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
    
def test_class_bind(dispatcher, cls):
    """Test class-level bind."""
    cls.bind(dispatcher)
    instance_a = cls()
    instance = cls()
    instance.mykeyword = "Hello"
    
    assert "callback" in instance.called
    assert "prewrite" in instance.called
    assert "preread" not in instance.called
    assert dispatcher["MYKEYWORD"]["value"] == "Hello"
    assert "preread" not in instance.called
    
    value = instance.mykeyword
    assert "preread" in instance.called
    
def test_class_bind_no_arguments(cls):
    """Test class-level bind with no service specified."""
    with pytest.raises(ServiceNotBound):
        cls.bind()
    
def test_descriptor_repr(dispatcher, cls):
    """Test the descriptor repr"""
    assert repr(cls.mykeyword) == "<KeywordDescriptor name=MYKEYWORD>"
    cls.bind(dispatcher)
    instance = cls()
    assert repr(cls.mykeyword) == "<KeywordDescriptor name=MYKEYWORD bound to {0!r}>".format(dispatcher)
    
def test_initial(dispatcher, cls):
    """Test the integrity checking for keywords."""
    instance = cls()
    assert instance.mykeyword == "SomeValue"
    instance.bind(dispatcher)
    assert instance.mykeyword == "SomeValue"
    
def test_initial_set_value(dispatcher, cls):
    """docstring for test_initial_set_value"""
    instance = cls()
    assert instance.mykeyword == "SomeValue"
    instance.mykeyword = "SomeValue2"
    assert instance.mykeyword == "SomeValue2"
    instance.bind(dispatcher)
    assert instance.mykeyword == "SomeValue2"
    assert dispatcher['MYKEYWORD']['value'] == "SomeValue2"
    
def test_initial_collision(dispatcher, cls):
    """Test an initial value collision."""
    instance = cls()
    dispatcher["MYKEYWORD"].modify("SomeValue3")
    
    with pytest.raises(IntegrityError):
        instance.bind(dispatcher)
    
def test_initial_no_value(dispatcher, cls):
    """Test the initial value case when there is no initial value."""
    cls.mykeyword._initial = None
    instance = cls()
    dispatcher['MYKEYWORD'].modify("SomeValue3")
    
    instance.bind(dispatcher)
    assert instance.mykeyword == "SomeValue3"
    
def test_initial_typed(dispatcher, cls):
    """Test the initial value when it should cause a type error."""
    instance = cls()
    cls.typedkeyword._initial = "SomeValue"
    with pytest.raises(ValueError):
        instance.bind(dispatcher)
    
def test_initial_failed_type(dispatcher, cls):
    """docstring for test_initial_failed_type"""
    instance = cls()
    cls.typedkeyword._initial = object()
    with pytest.raises(TypeError):
        instance.bind(dispatcher)
    
def test_readonly_and_writeonly():
    """Test making a keyword descriptor both readonly and writeonly."""
    with pytest.raises(ValueError):
        KeywordDescriptor("SOMEKEYWORD", readonly=True, writeonly=True)
    
def test_readonly(dispatcher):
    """Test a read-only keyword"""
    kwd = KeywordDescriptor("SOMEKEYWORD", readonly=True)
    kwd.service = dispatcher
    dispatcher["SOMEKEYWORD"].modify("SomeValue")
    assert kwd.__get__(object(), object) == "SomeValue"
    with pytest.raises(ValueError):
        kwd.__set__(None, "value")
        
def test_writeonly(dispatcher):
    """docstring for test_writeonly"""
    kwd = KeywordDescriptor("SOMEKEYWORD", writeonly=True)
    kwd.service = dispatcher
    dispatcher["SOMEKEYWORD"].modify("SomeValue")
    kwd.__set__(object(), "value")
    assert dispatcher["SOMEKEYWORD"]['value'] == "value"
    with pytest.raises(ValueError):
        kwd.__get__(object(), object)
        
def test_event_class_reprs(dispatcher, cls):
    """Test the REPR methods of event classes."""
    from .events import _KeywordEvent, _DescriptorEvent, _KeywordListener
    
    kwd = dispatcher["SOMEKEYWORD"]
    instance = cls()
    
    de = _DescriptorEvent("preread")
    assert repr(de) == "<_DescriptorEvent name=preread>"
    
    ke = _KeywordEvent(kwd, instance, de)
    expected = "<_KeywordEvent name=preread at "
    assert repr(ke)[:len(expected)] == expected
    
    kl = _KeywordListener(kwd, instance, de)
    expected = "<_KeywordListener name=preread at "
    assert repr(kl)[:len(expected)] == expected
    
def test_multiple_binds_other_serivce(dispatcher, config, cls):
    """Test for binds against multiple services"""
    from Cauldron import DFW
    svc = DFW.Service("OTHERSERVCE", config)
    try:
        instance = cls()
        instance.bind(dispatcher)
        with pytest.raises(ServiceAlreadyBound):
            instance.bind(svc)
    finally:
        svc.shutdown()
    
def test_multiple_binds_initial_values(dispatcher):
    """Test for multiple binds with initial values."""
    class MKO(DescriptorBase):
        """MultipleBind Keyword Test class!"""
        mykeyword = KeywordDescriptor("MYKEYWORD", initial="SomeValue")
    
    MKO.bind(dispatcher)
    i1 = MKO()
    i1.mykeyword = "OtherValue"
    # Should be fine, won't initialize, already bound.
    i2 = MKO()
    
    # This is definitley a hack to unbind, but we can't cause
    # the fixture 'dispatcher' to go out of scope.
    assert MKO.mykeyword._bound
    del MKO.mykeyword.service
    MKO.mykeyword._bound = False
    assert not MKO.mykeyword._bound
    
    # Now if we bind again, we should get
    # an IntegrityError when we try to instantiate
    # an instance, as the value was already set.
    MKO.bind(dispatcher)
    with pytest.raises(IntegrityError):
        i3 = MKO()
