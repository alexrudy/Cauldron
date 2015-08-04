# We don't want to export all of the definitions in version.py, just the
# version function itself. Delete the reference after appending our local
# version number.
from __future__ import absolute_import
from . import version
version.append ('$Revision: 83053 $')

__all__ = ('bundles',
       'dictionary',
       'get',
       'getFilename',
       'getKeywordName',
       'getValue',
       'id',
       'index',
       'keywordId',
       'Service',
       'sortStringAsNumber',
       'version')

#
# #
# Sanity checks. The full check for RELDIR and LROOT is done here, since
# there is no guarantee that the importer of this module is using kpython.
# #
#

import os
import sys

# Check for RELDIR environment variable.

if 'RELDIR' in os.environ:
    pass
else:
    os.environ['RELDIR'] = '/data/kroot'


# Check for LROOT environment variable. As of June 2011, there is potentially
# a default value for LROOT available via kroot/etc/defs.shared.mk (rev 8.4).

if 'LROOT' in os.environ:
    pass
elif '/data/lroot' != '':
    os.environ['LROOT'] = '/data/lroot'


# $(RELDIR)/lib/python and $(RELDIR)/lib should be in sys.path in order to
# safely import the ktl module.

# reldir_lib = os.path.join (os.environ['RELDIR'], 'lib')
# reldir_lib_python = os.path.join (reldir_lib, 'python')
#
# if reldir_lib_python in sys.path:
#     pass
# else:
#     sys.path.append (reldir_lib_python)
#
# if reldir_lib in sys.path:
#     pass
# else:
#     sys.path.append (reldir_lib)
#
#
# # Done with the safety dance, clean up the module namespace.
#
# del reldir_lib
# del reldir_lib_python
del os
del sys


from . import get
from . import id
from .parser import bundles, dictionary, includes, index
from .Service import Service
from .sort import stringAsNumber as sortStringAsNumber
from .version import version

# Backwards-compatibility.
from .get import filename as getFilename
from .get import keywordName as getKeywordName
from .get import value as getValue
from .id import generate as keywordId

MAX_KEYWORD_ID = id.generate.max

