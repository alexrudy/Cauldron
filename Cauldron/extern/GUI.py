import sys
from .core import import_mod
from ..api import install, guard_use

guard_use("importing the GUI module")
install()
from . import WeakRef
sys.modules["WeakRef"] = WeakRef
import_mod(['GUI','Cauldron.bundled.GUI'], __name__)
