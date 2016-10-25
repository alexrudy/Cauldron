import imp
import sys
from distutils.version import StrictVersion

__all__ = ['import_mod']

def _find_module(name, path=None):
    """
    Alternative to `imp.find_module` that can also search in subpackages.
    """

    parts = name.split('.')

    for part in parts:
        if path is not None:
            path = [path]

        fh, path, descr = imp.find_module(part, path)

    return fh, path, descr


def import_mod(search_path=[], name="", min_version=None):
    for mod_name in search_path:
        try:
            mod_info = _find_module(mod_name)
        except ImportError:
            continue
            
        if mod_name in sys.modules:
            sys.modules[name] = sys.modules[mod_name]
            break
        else:
            sys.modules[name] = imp.load_module(mod_name, *mod_info)
            break
    else:
        raise ImportError(
            "Cauldron requires the {0} module with a minimum version {1}.".format(name, min_version))
