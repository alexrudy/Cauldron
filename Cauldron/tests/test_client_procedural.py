# -*- coding: utf-8 -*-

import pytest

from test_client import service

def test_read_write(service, servicename, keyword_name):
    """Test a write method."""
    
    from Cauldron.ktl.procedural import read, write
    write(servicename, keyword_name, "10")
    assert read(servicename, keyword_name) == "10"