import version
version.append ('$Revision: 91402 $')
del version

''' Provide a queue mechanism to buffer KTL events. This is
    necessary because Tkinter sometimes rejects calls from threads
    that did not invoke the root Tk() instance. Another example:

    http://code.activestate.com/recipes/82965

    All function calls invoked as a result of KTL callbacks must
    land in this queue; consumers of this queue (of which there
    is exactly one, associated with 'the Tkinter thread') will
    then invoke the queued callbacks to safely modify any Tkinter
    objects.

    This queue is also leveraged to handle pending image redraw
    events, rather than mantain a separate mechanism to process
    such requests. While drawing an image will generally require
    invoking a Tkinter function in order for the change to be
    visible, it is possible to have invisible image manipulation
    take place.
'''

import collections
import threading
import Tkinter


# How responsive should the GUI be to asynchronous events? The value
# below represents how often the GUI will "poll" for keyword events,
# in milliseconds. If you set this value too low, the computer will
# spend all of its time in the event check loop; if you set it too
# high, the GUI will feel sluggish in response to value changes.

# 20 ms is 50 Hz, comparable to screen refresh rates.

delay = 20

pending = collections.deque ()

get = pending.popleft
put = pending.append


class ShutdownError (RuntimeError):
	pass


def doneNoisily (*ignored, **also_ignored):
	raise ShutdownError, 'event processing is shut down'


def doneQuietly (*ignored, **also_ignored):
	return


def shutdown ():
	''' Indicate that events should no longer be processed.
	'''

	global get
	global put

	get = doneNoisily
	put = doneQuietly


def queue (function, *arguments):
	''' Take arbitrary arguments and queue them up as a two-item
	    tuple, the callable function and a tuple of everything else.
	'''

	if callable (function):
		pass
	else:
		raise TypeError, 'function must be callable'


	put ((function, arguments))


def tkSet (tk_object, attribute, new_value):
	''' Set the 'attribute' item of the tk_object to the new_value.
	    This helper function is used in conjuction with :func:`queue`,
	    so that callbacks from background threads can safely request
	    updates to displayed elements.
	'''

	changed = False

	try:
		if tk_object[attribute] != new_value:
			tk_object[attribute] = new_value
			changed = True

	except Tkinter.TclError:
		# The containing widget went away
		# before it could be manipulated.

		pass

	return changed
