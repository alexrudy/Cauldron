# -*- coding: utf-8 -*-

import pytest
import os

pytestmark = pytest.mark.usefixtures("teardown_cauldron")

@pytest.fixture
def xmlpath(xmldir, servicename):
    """XML Directory path"""
    return os.path.join(xmldir, 'data', servicename)

def test_xml_index(xmlpath, servicename):
    """Test the XML index"""
    from ..bundled import ktlxml
    index = ktlxml.index(servicename, directory=xmlpath)
    
def test_xml_Service(xmlpath, servicename):
    """Test the XML service object."""
    from ..bundled import ktlxml
    xml = ktlxml.Service(servicename, directory=xmlpath)
    assert "LOOP" in xml
    
def test_Service_with_xml(xmlvar, backend, servicename, config):
    """Test a service with XML."""
    from Cauldron import DFW
    svc = DFW.Service(servicename, config)
    try:
        assert svc.xml is not None
        assert "LOOP" in svc
        assert "KEYWORD" not in svc
        kwd = svc["KEYWORD"]
        assert "KEYWORD" in svc
        kwd = svc["LOOP"]
        assert kwd.KTL_TYPE == 'enumerated'
    finally:
        svc.shutdown()
    
def test_Service_with_strict_xml(backend, servicename, config, dispatcher_name):
    """Test the backend with strict xml enabled, so it should raise an exception."""
    from Cauldron.api import use_strict_xml
    use_strict_xml()
    from Cauldron import DFW
    
    os.environ.pop('RELDIR', None)
    with pytest.raises(KeyError):
        svc = DFW.Service(servicename, config, dispatcher=dispatcher_name)
    os.environ['RELDIR'] = "directory/does/not/exist"
    with pytest.raises(IOError):
        svc = DFW.Service(servicename, config, dispatcher=dispatcher_name)
    

def test_Keyword_with_xml(xmlvar, dispatcher):
    """Test the backend with XML enabled."""
    keyword = dispatcher['LOOP']
    
def test_Keyword_with_strict_xml(strictxml, dispatcher):
    """Test keyword with strict xml"""
    keyword = dispatcher['LOOP']
    
    assert keyword.initial == "Open"
    
    with pytest.raises(KeyError):
        dispatcher["OTHERKEYWORD"]
        

def test_Service_with_dispatcher(xmlvar, backend, servicename, config):
    """XML service with dispatcher explicitly set."""
    from Cauldron import DFW
    svc = DFW.Service(servicename, config, dispatcher='+service+_dispatch_2')
    try:
        keyword = svc['LOOP']
    finally:
        svc.shutdown()
    
def test_Service_with_wrong_dispatcher(strictxml, backend, servicename, config):
    """XML service with dispatcher explicitly set."""
    from Cauldron import DFW
    from Cauldron.exc import WrongDispatcher
    svc = DFW.Service(servicename, config, dispatcher='+service+_dispatch_2')
    try:
        with pytest.raises(WrongDispatcher):
            keyword = svc['LOOP']
    finally:
        svc.shutdown()