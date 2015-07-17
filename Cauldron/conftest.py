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

def clear_registry():
    """Clear the redis registry."""
    import redis
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    r.delete(REDIS_SERVICES_REGISTRY)

try:
    import redis
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    r.ping()
    from .redis.common import configure_pool, REDIS_SERVICES_REGISTRY
    configure_pool(host='localhost', port=6379, db=0)
    clear_registry()
except Exception as e:
    # If, for any reason, REDIS is not available, just don't test against it.
    pass
else:
    PYTEST_HEADER_MODULES['redis'] = 'redis'
    available_backends.append("redis")

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

def fail_if_not_teardown():
    """Fail if teardown has not happedned properly."""
    from Cauldron.api import teardown
    teardown()
    failures = ["DFW", "ktl", "_DFW", "_ktl"]
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
    
@pytest.fixture(scope='function')
def teardown_cauldron(request):
    """docstring for teardown_cauldron"""
    from Cauldron.api import teardown
    teardown()
    request.addfinalizer(fail_if_not_teardown)
    return None

@pytest.fixture(params=available_backends)
def backend(request):
    """The backend name."""
    from Cauldron.api import use, teardown
    use(request.param)
    request.addfinalizer(fail_if_not_teardown)
    if request.param == "redis":
        request.addfinalizer(clear_registry)
    return request.param

@pytest.fixture
def dispatcher(backend, servicename, config):
    """Establish the dispatcher for a particular kind of service."""
    from Cauldron import DFW
    return DFW.Service(servicename, config)
    
@pytest.fixture
def client(backend, servicename):
    """Test a client."""
    from Cauldron import ktl
    return ktl.Service(servicename)
