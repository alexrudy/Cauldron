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
    PYTEST_HEADER_MODULES['Astropy'] = 'astropy'
    del PYTEST_HEADER_MODULES['h5py']
    del PYTEST_HEADER_MODULES['Scipy']
    del PYTEST_HEADER_MODULES['Matplotlib']
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

available_backends = ["local"]

try:
    import zmq
except ImportError:
    pass
else:
    from . import registry
    PYTEST_HEADER_MODULES['zmq'] = 'zmq'
    if "zmq" in registry.keys():
        available_backends.append("zmq")
    ROUTER = None


import pkg_resources
import os
from .utils._weakrefset import WeakSet

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
def config():
    """DFW configuration."""
    return None
    
@pytest.fixture
def check_teardown(request):
    """Check that a module has been torn down."""
    request.addfinalizer(fail_if_not_teardown)

SEEN_THREADS = WeakSet()
def fail_if_not_teardown():
    """Fail if teardown has not happedned properly."""
    from Cauldron.api import teardown, CAULDRON_SETUP
    teardown()
    failures = ["DFW", "ktl", "_DFW", "_ktl"]
    if CAULDRON_SETUP:
        pytest.fail("Cauldron is marked as 'setup'.")
    for module in sys.modules:
        for failure in failures:
            if failure in module.split("."):
                mod = sys.modules[module]
                pytest.fail("Module {0}/{1} not properly torn down.".format(module, sys.modules[module]))
    try:
        from Cauldron import DFW
    except ImportError as e:
        pass
    else:
        pytest.fail("Shouldn't be able to import DFW now!")
    
    import threading, time
    if threading.active_count() > 1:
        time.sleep(0.1) #Allow zombies to die!
    count = 0
    for thread in threading.enumerate():
        if not thread.daemon and thread not in SEEN_THREADS:
            count += 1
            SEEN_THREADS.add(thread)
    if count > 1:
        pytest.fail("{0:d} non-deamon thread{1:s} left alive!\n{2!s}".format(count-1, "s" if (count-1)>1 else "",
            "\n".join([repr(thread) for thread in threading.enumerate()])))
    
@pytest.fixture(scope='function')
def teardown_cauldron(request):
    """docstring for teardown_cauldron"""
    request.addfinalizer(fail_if_not_teardown)
    return None

@pytest.fixture(params=available_backends)
def backend(request):
    """The backend name."""
    global ROUTER
    from Cauldron.api import use, teardown, CAULDRON_SETUP
    if request.param == 'zmq' and ROUTER is None:
        from Cauldron.zmq.router import ZMQRouter
        ROUTER = ZMQRouter.daemon()
    use(request.param)
    request.addfinalizer(fail_if_not_teardown)
    return request.param

@pytest.fixture
def dispatcher(request, backend, servicename, config):
    """Establish the dispatcher for a particular kind of service."""
    from Cauldron import DFW
    svc = DFW.Service(servicename, config)
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
