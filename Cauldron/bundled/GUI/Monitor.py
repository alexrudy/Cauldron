import version
version.append ('$Revision: 84796 $')
del version


import collections
import threading


pending = collections.deque ()
processors = []

get = pending.popleft
put = pending.append


def processor (function):
	''' A processor function is expected to have an .active attribute.
	    If .active is False, the function will be called when
	    Monitor.queue() is invoked; if .active is True, the function
	    will not be called.
	'''

	# Instance methods have a im_func attribute that will
	# have the .active attribute.

	try:
		container = function.im_func

	except AttributeError:
		container = function


	if hasattr (container, 'active'):
		pass
	else:
		raise RuntimeError, 'function must have a .active attribute'

	processors.append (function)


def queue (keyword):

	put (keyword)

	for processor in processors:
		try:
			container = processor.im_func
		except AttributeError:
			container = processor

		if container.active == False:
			container.active = True
			processor ()
