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
import sys
import six
import warnings
import pkg_resources

from six.moves import configparser

from .exc import ConfigurationMissing
from . import registry

BASENAME = ".".join(__name__.split(".")[:-1])

__all__ = ['default_configuration', 'read_configuration', 'cauldron_configuration']

def default_configuration():
    """Get the default configuration object."""
    config = configparser.ConfigParser()
    with open(pkg_resources.resource_filename(__name__, 'data/defaults.cfg')) as fp:
        config.readfp(fp)
    return config

def read_configuration(configuration_location = None):
    """Read a configuration from a filepath or a configuration object."""
    
    if configuration_location is None:
        return cauldron_configuration
    elif isinstance(configuration_location, configparser.ConfigParser):
        return configuration_location
    else:
        configuration_location = six.text_type(configuration_location)
    
    
    configuration_location = os.path.abspath(os.path.expanduser(configuration_location))
    
    try:
        with open(configuration_location, 'r') as fp:
            cauldron_configuration.readfp(fp)
    except configparser.ParsingError as e:
        warnings.warn("Can't parse configuration file '{0:s}'".format(configuration_location), ConfigurationMissing)
    except IOError:
        warnings.warn("Can't locate configuration file '{0:s}'.".format(configuration_location), ConfigurationMissing)
    return cauldron_configuration
    
def get_configuration():
    """Return the active configuration object."""
    Cauldron = sys.modules[BASENAME]
    return Cauldron.configuration
    
_timeouts = {}
def get_timeout(timeout):
    """Get the configured default timeout."""
    if timeout is None:
        config = get_configuration()
        try:
            timeout = _timeouts[id(config)]
        except KeyError:
            try:
                timeout = config.getfloat('core', 'timeout')
            except configparser.NoOptionError:
                pass
            _timeouts[id(config)] = timeout
    return timeout
    
@registry.dispatcher.setup_for('all')
@registry.client.setup_for('all')
def setup_configuration():
    """Set up the configuration when the API starts."""
    Cauldron = sys.modules[BASENAME]
    Cauldron.configuration = cauldron_configuration
    
@registry.dispatcher.teardown_for('all')
@registry.client.teardown_for('all')
def reset_configuration():
    """Reset the global configuration"""
    global cauldron_configuration
    cauldron_configuration = default_configuration()
    Cauldron = sys.modules[BASENAME]
    if hasattr(Cauldron, 'configuration'):
        del Cauldron.configuration
    
reset_configuration()

