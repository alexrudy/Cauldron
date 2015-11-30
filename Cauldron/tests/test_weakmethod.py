# -*- coding: utf-8 -*-
"""
Tests for the weak method class and the Callbacks container.
"""

import pytest
import weakref

from ..utils.callbacks import WeakMethod, Callbacks

def check_weak_method(wm, func, instance=None):
    """Check the weak method object."""
    assert wm.valid
    assert wm.check()
    if instance is None:
        assert wm.func == func
        assert not wm.method
        assert wm.get() == func
    else:
        assert wm.method
        assert wm.instance == instance
        assert wm.get() == func.__get__(instance, type(instance))
    assert wm.__doc__ == func.__doc__
    assert isinstance(hash(wm), int)

def test_wm_init():
    """Test init failure"""
    with pytest.raises(TypeError):
        wm = WeakMethod(1)
    
def test_wm_func():
    """Test with a function."""
    def my_function():
        """docstring"""
        return 10
    
    wm = WeakMethod(my_function)
    assert wm() == 10
    check_weak_method(wm, my_function)
    
@pytest.fixture
def my_class():
    """docstring for my_clas"""
    class my_class(object):
        value = 20
        def my_method(self):
            """method docstring"""
            return self.value
            
        @classmethod
        def my_classmethod(cls):
            """classmethod docstring"""
            return cls.value * cls.value
    
    return my_class
    
def test_wm_bound(my_class):
    """Test with a bound function."""
    my_instance = my_class()
    wm = WeakMethod(my_instance.my_method)
    assert wm() == 20
    check_weak_method(wm, my_instance.my_method, my_instance)
    
def test_manual_bind(my_class):
    """Test a bind manually."""
    wm = WeakMethod(my_class.my_method)
    assert wm.method
    with pytest.raises(TypeError):
        wm()
    my_instance = wm.instance = my_class()
    assert wm.method
    assert wm() == 20
    check_weak_method(wm, my_class.my_method, my_instance)
    
def test_hash(my_class):
    """Test that the hashes and equality methods work."""
    def my_function():
        """docstring"""
        return 10
    my_instance = my_class()
    a_bound = WeakMethod(my_instance.my_method)
    m_bound = WeakMethod(my_class.my_method)
    m_bound.instance = my_instance
    n_bound = WeakMethod(my_function)
    
    assert hash(a_bound) == hash(m_bound)
    assert a_bound == m_bound
    assert hash(a_bound) != hash(n_bound)
    assert a_bound != n_bound
    assert a_bound != my_instance.my_method
    
def test_copy(my_class):
    """Test copying."""
    my_instance = my_class()
    a_bound = WeakMethod(my_instance.my_method)
    c_bound = a_bound.copy()
    
    assert hash(a_bound) == hash(c_bound)
    assert a_bound == c_bound
    assert a_bound is not c_bound
    
def test_drop_instance_reference(my_class):
    """Test dropping references"""
    my_instance = my_class()
    wm = WeakMethod(my_instance.my_method)
    assert wm.instance is my_instance
    assert wm.valid
    del my_instance
    assert not wm.valid
    with pytest.raises(weakref.ReferenceError):
        wm.get()
    with pytest.raises(weakref.ReferenceError):
        wm()
    
def test_drop_func_reference():
    """docstring for test_drop_func_reference"""
    def my_function():
        """docstring"""
        return 10
    
    wm = WeakMethod(my_function)
    assert wm.func is my_function
    assert wm.valid
    del my_function
    assert not wm.valid
    with pytest.raises(weakref.ReferenceError):
        wm.get()
    with pytest.raises(weakref.ReferenceError):
        wm()
        
def test_callback():
    """Test the invalidation callback."""
    
    def cb(self):
        """Callback"""
        cb.invalid.add(self)
    cb.invalid = set()
    
    def my_function():
        """docstring"""
        return 10
    
    wm = WeakMethod(my_function, cb)
    assert wm.func is my_function
    assert wm.valid
    del my_function
    assert not wm.valid
    with pytest.raises(weakref.ReferenceError):
        wm.get()
    with pytest.raises(weakref.ReferenceError):
        wm()
    assert wm in cb.invalid
        
def test_delete_instance(my_class):
    """Test explicitly deleting an instacne."""
    my_instance = my_class()
    m_bound = WeakMethod(my_class.my_method)
    assert m_bound.method
    m_bound.instance = my_instance
    assert m_bound.method
    del m_bound.instance
    assert not m_bound.method
    with pytest.raises(TypeError):
        m_bound()
    
    

def test_callbacks_collection_type():
    """Test the type-safety."""
    cbs = Callbacks()
    with pytest.raises(TypeError):
        cbs.add(1)
    with pytest.raises(TypeError):
        Callbacks(10,20)

def test_callbacks_collection():
    """Test a collection of callbacks."""
    def my_function():
        """docstring"""
        return 10
    def other_function():
        """docstring"""
        return 30
        
    cbs = Callbacks(*[my_function, my_function, other_function])
    assert len(cbs) == 2
    assert my_function in cbs
    assert other_function in cbs
    
def test_callbacks_repr():
    """Test callbacks representation"""
    cbs = Callbacks()
    assert repr(cbs) == "<Callbacks []>"
    
def test_callbacks_weak():
    """Test callbacks weak"""
    def my_function():
        """docstring"""
        return 10
    def other_function():
        """docstring"""
        return 30
        
    cbs = Callbacks(*[my_function, my_function, other_function])
    assert len(cbs) == 2
    del other_function
    assert len(cbs) == 1
    
def test_callbacks_iterating():
    """Test callbacks during iteration."""
    def my_function():
        """docstring"""
        return 10
    def other_function():
        """docstring"""
        return 30
        
    cbs = Callbacks(*[my_function, my_function, other_function])
    assert len(cbs) == 2
    c = 0
    for f in cbs:
        for f in cbs:
            del other_function
        c += 1
        assert len(cbs) == 1
        assert len(cbs.data) == 2
    assert c == 1
    assert len(cbs) == 1
    
def test_prepend():
    """Test prepend."""
    def my_function():
        """docstring"""
        return 10
    def other_function():
        """docstring"""
        return 30
        
    cbs = Callbacks(*[my_function, my_function, other_function])
    cbs.prepend(other_function)
    for cb in cbs:
        assert cb() == other_function()
        break
    
