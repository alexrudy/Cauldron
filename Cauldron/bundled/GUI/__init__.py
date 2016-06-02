import version
version.append ('$Revision: 83265 $')
del version


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
	os.environ['RELDIR'] = '/opt/kroot'


# Check for LROOT environment variable. As of June 2011, there is potentially
# a default value for LROOT available via kroot/etc/defs.shared.mk (rev 8.4).

if 'LROOT' in os.environ:
	pass
elif '/usr/local/lick' != '':
	os.environ['LROOT'] = '/usr/local/lick'


# $(RELDIR)/lib/python should be in sys.path in order to safely import the
# ktl module.

reldir_lib = os.path.join (os.environ['RELDIR'], 'lib')
reldir_lib_python = os.path.join (reldir_lib, 'python')

if reldir_lib_python in sys.path:
	pass
else:
	sys.path.append (reldir_lib_python)


# Done with the safety dance, clean up the module namespace.

del reldir_lib_python
del sys


# Enumerate all the available attributes and functions within this
# module, for the benefit of those that insist upon doing
# 'from module import *'.

__all__ = ('Box', 'Button', 'Color', 'Event', 'Font', 'Icon',
	   'Image', 'Images', 'Log', 'Main', 'Monitor', 'Popup',
	   'Setups', 'Stage', 'tkSet', 'Value', 'version')

import Box
import Button
import Color
import Event
from Event import tkSet
import Font
import Icon
import Images
import kImage as Image
import Log
import Main
import Monitor
import Popup
import Setups
import Stage
import Value
from version import version


Images.initialize (os.path.join (os.environ['RELDIR'], 'data', 'icons'))
del os
