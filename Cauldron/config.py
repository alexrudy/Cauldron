#
#  config.py
#  cauldron
#
#  Created by Alexander Rudy on 2015-11-21.
#  Copyright 2015 Alexander Rudy. All rights reserved.
#
"""
Basics for handling Cauldron configuration files.
"""

import os
import six
import warnings
import pkg_resources

from six.moves import configparser

from .exc import ConfigurationMissing

__all__ = ['default_configuration', 'read_configuration', 'set_module_configuration', 'get_module_configuration']

def default_configuration():
    """Get the default configuration object."""
    config = configparser.ConfigParser()
    with pkg_resources.resource_stream(__name__, 'data/defaults.cfg') as fp:
        config.readfp(fp)
    return config

def read_configuration(configuration_location = None, config = None):
    """Read a configuration from a filepath."""
    
    if config is None:
        if isinstance(configuration_location, configparser.ConfigParser):
            return configuration_location
        config = default_configuration()
    elif not isinstance(config, configparser.ConfigParser):
        raise TypeError("'config' must be a subclass of {0!r}".format(configparser.ConfigParser))
    
    if configuration_location is None:
        return config
    else:
        configuration_location = six.text_type(configuration_location)
    
    
    configuration_location = os.path.abspath(os.path.expanduser(configuration_location))
    
    try:
        with open(configuration_location, 'r') as fp:
            config.readfp(fp)
    except configparser.ParsingError as e:
        warnings.warn("Can't parse configuration file '{0:s}'".format(configuration_location), ConfigurationMissing)
    except IOError:
        warnings.warn("Can't locate configuration file '{0:s}'.".format(configuration_location), ConfigurationMissing)
    return config
    
_cauldron_configuration = default_configuration()
    
def set_module_configuration(configuration_location = None):
    """Read a configuration file into the module-level configuration object."""
    global _cauldron_configuration
    _cauldron_configuration = read_configuration(configuration_location, _cauldron_configuration)
    
def get_module_configuration():
    """Get the module level configuration item."""
    return _cauldron_configuration