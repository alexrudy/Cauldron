# -*- coding: utf-8 -*-
"""
Test configuration items / tools.
"""

import pytest

from Cauldron.config import read_configuration

CONFIGFILE = """
[new-section]
backend = no

"""

@pytest.fixture
def configfile(tmpdir):
    """Test a configuration file path."""
    cfg = tmpdir.join("cauldron.cfg")
    cfg.write(CONFIGFILE)
    return str(cfg)
    
@pytest.fixture
def badconfigfile(tmpdir):
    """Test a configuration file path."""
    cfg = tmpdir.join("cauldron.cfg")
    cfg.write(CONFIGFILE)
    cfg.write("[bogus-section]\n")
    cfg.write("bad = option = values?")
    return str(cfg)

def test_read_configuration_path(configfile):
    """Read a configuration file from a filepath."""
    cfg = read_configuration(configfile)
    assert cfg.has_section("new-section")
    assert cfg.has_option("new-section", "backend")

def test_read_nonexistent_path(tmpdir):
    """Ensure that we read safely from a non-existent path."""
    cfg = read_configuration(tmpdir.join("does-not-exist.cfg"))
    assert cfg.has_option("zmq", "broker") # Test that we still got the default configuration.
    
def test_read_bad_configuration_file(badconfigfile):
    """Test that we can plow through a bad config file."""
    cfg = read_configuration(badconfigfile)
    assert cfg.has_option("zmq", "broker") # Test that we still got the default configuration.
    