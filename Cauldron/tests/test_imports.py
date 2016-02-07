# -*- coding: utf-8 -*-
"""
Tests that ensure that Cauldron imports work.
"""

import pytest
import sys

pytestmark = pytest.mark.usefixtures("teardown_cauldron")


def test_guard():
    """Test that imports are guarded."""
    from Cauldron.api import use, teardown
    
    with pytest.raises(ImportError):
        from Cauldron import ktl
    with pytest.raises(ImportError):
        from Cauldron import DFW
    use("local")
    from Cauldron import DFW, ktl
    del DFW, ktl
    teardown()
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
    assert hasattr(ktl.Keyword, 'Keyword')
    assert hasattr(DFW.Keyword, 'Keyword')

def test_import_duplicates():
    """Test importing Cauldron modules in different ways."""
    from Cauldron.base.client import Keyword
    from Cauldron.api import use
    use("local")
    from Cauldron import ktl, DFW
    from Cauldron import _ktl, _DFW
    assert dir(ktl) == dir(_ktl)
    assert dir(DFW) == dir(_DFW)
    assert issubclass(ktl.Keyword.Keyword, Keyword)
    
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

def test_double_teardown():
    """Test teardown twice"""
    from Cauldron.api import use, install, teardown
    use("local")
    from Cauldron import ktl
    del ktl
    
    from Cauldron import DFW
    del DFW
    
    install()
    teardown()
    teardown()
    
    with pytest.raises(ImportError):
        from Cauldron import ktl
    with pytest.raises(ImportError):
        from Cauldron import DFW
    
    assert "DFW" not in sys.modules
    assert "ktl" not in sys.modules
    
    use('local')
    from Cauldron import ktl, DFW

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
    