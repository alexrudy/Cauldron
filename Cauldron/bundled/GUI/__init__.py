import version
version.append ('$Revision: 83265 $')
del version

import os, pkg_resources

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

path = pkg_resources.resource_filename("Cauldron", "data/reldir/data/icons")
Images.initialize (path)