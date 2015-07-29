# -*- coding: utf-8 -*-

import pytest

pytestmark = pytest.mark.usefixtures("teardown_cauldron")

def test_xml_index(xmldir, servicename):
    """Test the XML index"""
    from ..bundled import ktlxml
    
    index = ktlxml.index(servicename, directory=xmldir)
    
def test_xml_Service(xmldir, servicename):
    """Test the XML service object."""
    from ..bundled import ktlxml
    xml = ktlxml.Service(servicename, directory=xmldir)
    assert "LOOP" in xml