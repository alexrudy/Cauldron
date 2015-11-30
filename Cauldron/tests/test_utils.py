# -*- coding: utf-8 -*-

import pytest

from Cauldron.utils.helpers import _Setting, api_not_required
from Cauldron.exc import CauldronAPINotImplemented

def test_setting_inverse():
    """Make a setting and test inverse setting."""
    setting = _Setting("TESTSETTING", False)
    inv = setting.inverse
    assert not setting
    assert inv
    
    inv.off()
    assert setting
    assert not inv
    
def test_setting_lock():
    """Test a setting lock."""
    lock = _Setting("TESTLOCK", False)
    setting = _Setting("TESTSETTING", False, lock=lock)
    setting.on()
    assert setting
    lock.on()
    with pytest.raises(RuntimeError):
        setting.off()
    assert setting
    lock.off()
    setting.off()
    assert not setting
    
def test_not_required():
    """Test the API not required decorator."""
    
    @api_not_required
    def some_not_required_method():
        """Documentation for some_not_required_method"""
        pass
        
    assert """Cauldron backends are not required to implement this function.""" in some_not_required_method.__doc__
    assert """some_not_required_method""" in some_not_required_method.__doc__
    
    with pytest.raises(CauldronAPINotImplemented):
        some_not_required_method()