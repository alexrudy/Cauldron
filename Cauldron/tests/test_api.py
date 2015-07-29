# -*- coding: utf-8 -*-
"""
Test API functions
"""

import pytest
pytestmark = pytest.mark.usefixtures("teardown_cauldron")


def test_api_unknown():
    """docstring for test_api_unknown"""
    from Cauldron.api import use
    with pytest.raises(ValueError):
        use("unknown_backend")
        
def test_setting():
    """Test the Setting object"""
    from Cauldron.api import _Setting
    MYSETTING = _Setting("MYSETTING", True)
    assert repr(MYSETTING) == "<Setting MYSETTING=True>"
    
def test_setting_toggles():
    """Test the Setting toggles."""
    from Cauldron.api import _Setting
    MYSETTING = _Setting("MYSETTING", True)
    assert MYSETTING
    MYSETTING.off()
    assert not MYSETTING
    MYSETTING.on()
    assert MYSETTING