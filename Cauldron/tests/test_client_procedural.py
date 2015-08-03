# -*- coding: utf-8 -*-

import pytest

from test_client import service

def test_read_write(service, servicename):
    """Test a write method."""
    
    from Cauldron.ktl.procedural import read, write
    write(servicename, "KEYWORD", "10")
    assert read(servicename, "KEYWORD") == "10"