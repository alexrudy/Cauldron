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
    
def test_xml_Service(xmlpath, servicename, keyword_name_ENUMERATED):
    """Test the XML service object."""
    from ..bundled import ktlxml
    xml = ktlxml.Service(servicename, directory=xmlpath)
    assert keyword_name_ENUMERATED in xml
    
def test_Service_with_xml(xmlvar, backend, servicename, config, missing_keyword_name, keyword_name_ENUMERATED):
    """Test a service with XML."""
    from Cauldron import DFW
    svc = DFW.Service(servicename, config, dispatcher='+service+_dispatch_1')
    try:
        assert svc.xml is not None
        assert keyword_name_ENUMERATED in svc
        assert missing_keyword_name not in svc
        kwd = svc[missing_keyword_name]
        assert missing_keyword_name in svc
        kwd = svc[keyword_name_ENUMERATED]
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
    

def test_Keyword_with_xml(xmlvar, dispatcher, keyword_name_ENUMERATED):
    """Test the backend with XML enabled."""
    keyword = dispatcher[keyword_name_ENUMERATED]
    
def test_Keyword_with_strict_xml(strictxml, dispatcher, keyword_name_ENUMERATED, missing_keyword_name):
    """Test keyword with strict xml"""
    keyword = dispatcher[keyword_name_ENUMERATED]
    
    assert keyword.initial == "Open"
    
    with pytest.raises(KeyError):
        dispatcher[missing_keyword_name]
        

def test_Service_with_dispatcher(xmlvar, backend, servicename, config, keyword_name_ENUMERATED, dispatcher_name):
    """XML service with dispatcher explicitly set."""
    from Cauldron import DFW
    svc = DFW.Service(servicename, config, dispatcher=dispatcher_name)
    try:
        keyword = svc[keyword_name_ENUMERATED]
    finally:
        svc.shutdown()
    
def test_Service_with_wrong_dispatcher(strictxml, backend, servicename, config, keyword_name_ENUMERATED, dispatcher_name2):
    """XML service with dispatcher explicitly set."""
    from Cauldron import DFW
    from Cauldron.exc import WrongDispatcher
    svc = DFW.Service(servicename, config, dispatcher=dispatcher_name2)
    try:
        with pytest.raises(WrongDispatcher):
            keyword = svc[keyword_name_ENUMERATED]
    finally:
        svc.shutdown()