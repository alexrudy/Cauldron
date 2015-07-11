# -*- coding: utf-8 -*-
"""
Tests that ensure that Cauldron imports work.
"""

import pytest
import sys

pytestmark = pytest.mark.usefixtures("teardown_cauldron")


def test_guard():
    """Test that imports are guarded."""
    with pytest.raises(ImportError):
        from Cauldron import ktl
    with pytest.raises(ImportError):
        from Cauldron import DFW
        
def test_reuse():
    """Test calling use twice."""
    from Cauldron.api import use, teardown
    use("local")
    with pytest.raises(RuntimeError):
        use("local")
        
    
def test_dangling_imports():
    """Test imports which are dangling."""
    from Cauldron.api import use
    use("local")
    from Cauldron import ktl, DFW
    
def test_teardown():
    """Test that imports are guarded after calling .teardown()"""
    from Cauldron.api import use, install, teardown
    use("local")
    from Cauldron import ktl
    del ktl
    
    from Cauldron import DFW
    del DFW
    
    install()
    teardown()
    with pytest.raises(ImportError):
        from Cauldron import ktl
    with pytest.raises(ImportError):
        from Cauldron import DFW
        
    assert "DFW" not in sys.modules
    assert "ktl" not in sys.modules

def test_install():
    """Test the install feature."""
    from Cauldron.api import use, install
    
    with pytest.raises(RuntimeError):
        install()
    
    use("local")
    install()
    
    import ktl
    import Cauldron.ktl
    assert ktl == Cauldron.ktl
    
    import DFW
    import Cauldron.DFW
    assert DFW == Cauldron.DFW
    