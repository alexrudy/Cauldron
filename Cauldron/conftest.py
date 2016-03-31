from __future__ import absolute_import

# this contains imports plugins that configure py.test for astropy tests.
# by importing them here in conftest.py they are discoverable by py.test
# no matter how it is invoked within the source tree.
from astropy.tests.pytest_plugins import *

## Uncomment the following line to treat all DeprecationWarnings as
## exceptions
# enable_deprecations_as_exceptions()

## Uncomment and customize the following lines to add/remove entries
## from the list of packages for which version numbers are displayed
## when running the tests
try:
    PYTEST_HEADER_MODULES['astropy'] = 'astropy'
    PYTEST_HEADER_MODULES.pop('h5py', None)
    PYTEST_HEADER_MODULES.pop('Scipy', None)
    PYTEST_HEADER_MODULES.pop('Matplotlib', None)
    PYTEST_HEADER_MODULES.pop('Pandas', None)
except NameError:  # needed to support Astropy < 1.0
    pass

## Uncomment the following lines to display the version number of the
## package rather than the version number of Astropy in the top line when
## running the tests.
# import os
#
## This is to figure out the affiliated package version, rather than
## using Astropy's
from . import version
#
try:
    packagename = os.path.basename(os.path.dirname(__file__))
    TESTED_VERSIONS[packagename] = version.version
except NameError:   # Needed to support Astropy <= 1.0.0
    pass

import pkg_resources
import os

from .test_helpers import fail_if_not_teardown, get_available_backends

available_backends = get_available_backends()
if "zmq" in available_backends:
    PYTEST_HEADER_MODULES['zmq'] = 'zmq'

def _pytest_get_option(config, name, default):
    """Get pytest options in a version independent way, with allowed defaults."""
    
    try:
        value = config.getoption(name, default=default)
    except Exception:
        try:
            value = config.getvalue(name)
        except Exception:
            return default
    return value
    

def pytest_configure(config):
    """Activate log capturing if appropriate."""

    if (not _pytest_get_option(config, 'capturelog', default=True)) or (_pytest_get_option(config, 'capture', default="no") == "no"):
        try:
            import lumberjack
            lumberjack.setup_logging("", mode='stream', level=1)
            lumberjack.setup_warnings_logger("")
        except:
            pass
    else:
        try:
            import lumberjack
            lumberjack.setup_logging("", mode='none', level=1)
            lumberjack.setup_warnings_logger("")
        except:
            pass

@pytest.fixture
def servicename():
    """Get the service name."""
    return "testsvc"
    
@pytest.fixture
def servicename2():
    """Get a second servicename"""
    return "testaltsvc"
    
MAX_KEYWORD_NUBMER = 4
def pytest_generate_tests(metafunc):
    for fixture in metafunc.fixturenames:
        if fixture.startswith("keyword_name_"):
            postfix = fixture[len("keyword_name_"):]
            metafunc.parametrize(fixture, ["KEYWORD_{0:s}".format(postfix)])
        elif fixture.startswith("keyword_name"):
            number = int("0"+fixture[len("keyword_name"):])
            if number > MAX_KEYWORD_NUBMER:
                raise ValueError("Fixture {0} doesn't represent a known keyword.".format(fixture))
            metafunc.parametrize(fixture, ["KEYWORD{0:d}".format(number)])
        if fixture.startswith("missing_keyword_name"):
            postfix = fixture[len("missing_keyword_name"):]
            metafunc.parametrize(fixture, ["MISSINGKEYWORD{0:s}".format(postfix)])
    
@pytest.fixture(scope='function')
def config(tmpdir):
    """DFW configuration."""
    from .config import cauldron_configuration
    cauldron_configuration.set("zmq", "broker", "inproc://broker")
    cauldron_configuration.set("zmq", "publish", "inproc://publish")
    cauldron_configuration.set("zmq", "subscribe", "inproc://subscribe")
    cauldron_configuration.set("core", "timeout", "5")
    return cauldron_configuration
    

@pytest.fixture(scope='function')
def teardown_cauldron(request):
    """A specific fixture to force cauldron teardown."""
    request.addfinalizer(fail_if_not_teardown)
    return None

@pytest.fixture(params=available_backends, scope='function')
def backend(request, config):
    """The backend name."""
    from Cauldron.api import use, teardown, CAULDRON_SETUP
    use(request.param)
    request.addfinalizer(fail_if_not_teardown)
    
    if request.param == 'zmq':
        from Cauldron.zmq.broker import ZMQBroker
        b = ZMQBroker.setup(config=config, timeout=0.01)
        if b:
            request.addfinalizer(b.stop)
    return request.param

@pytest.fixture
def dispatcher_name():
    """The dispatcher name"""
    return "+service+_dispatch_1"

@pytest.fixture
def dispatcher_name2():
    """The dispatcher name"""
    return "+service+_dispatch_2"


@pytest.fixture
def dispatcher(request, backend, servicename, config, dispatcher_name):
    """Establish the dispatcher for a particular kind of service."""
    from Cauldron import DFW
    svc = DFW.Service(servicename, config, dispatcher=dispatcher_name)
    request.addfinalizer(lambda : svc.shutdown())
    return svc
    
@pytest.fixture
def client(backend, servicename):
    """Test a client."""
    from Cauldron import ktl
    return ktl.Service(servicename)

@pytest.fixture
def xmldir(request):
    """XML Directory for testing."""
    path = pkg_resources.resource_filename("Cauldron", "data/xml")
    os.environ['RELDIR'] = "" # This must be set to some value. A key error is spuriously raised if RELDIR is not set.
    request.addfinalizer(xmlteardown)
    return os.path.abspath(path)

@pytest.fixture
def xmlvar(request, xmldir):
    """XML directory, and ensure it is set to the right environment variable."""
    reldir = os.environ['RELDIR'] = os.path.abspath(xmldir)
    request.addfinalizer(xmlteardown)
    return reldir
    
def xmlteardown():
    """Remove XML from the environment."""
    os.environ.pop('RELDIR', None)
    
@pytest.fixture
def strictxml(xmlvar):
    """Turn on strict xml"""
    from Cauldron.api import STRICT_KTL_XML
    STRICT_KTL_XML.on()
    return xmlvar
    
@pytest.fixture
def waittime():
    """Event wait time, in seconds."""
    return 0.1
