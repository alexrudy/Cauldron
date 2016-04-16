import version
version.append ('$Revision: 83203 $')
del version


import logging
import logging.handlers
import os
import sys
import time
import WeakRef		# provided by cvs/kroot/util/py-util


#
# #
# Initialize our syslog configuration.
# #
#

logger = logging.getLogger (__name__)
logger.setLevel (logging.DEBUG)

executable = os.path.basename (sys.argv[0])
formatter  = logging.Formatter ("%s: %%(message)s" % (executable))

arguments = {}
arguments['facility'] = 'local6'

if os.path.exists ('/dev/log'):
	arguments['address'] = '/dev/log'

handler = logging.handlers.SysLogHandler (**arguments)
handler.setLevel (logging.DEBUG)
handler.setFormatter (formatter)

logger.addHandler (handler)


sirens = []

def addSiren (siren):

	sirens.append (WeakRef.WeakRef (siren))



def alert (line):
	''' Write the line (without an appended newline) to any functions
	    appended to the sirens list. This typically includes MenuBar
	    objects.

	    The message will also be logged to syslog.
	'''

	logger = logging.getLogger (__name__)
	logger.info (line)

	delete = []

	for reference in sirens:

		function = reference ()

		if function == None:
			delete.append (reference)

		function (line)


	for reference in delete:

		sirens.remove (reference)



def error (line):
	''' Similar to alert(), but instead sends only to stderr and syslog.
	    the sirens list is not inspected, or used.
	'''

	logger = logging.getLogger (__name__)
	logger.error (line)

	sys.stderr.write ("%f %s\n" % (time.time (), line))

