import version
version.append ('$Revision: 83206 $')
del version


import tkFont


# Initial size.

size = '10'


# Initial font instances. If changed, these should be changed very early,
# right after creating a Main.Window instance.

button  = None
display = None
input   = None


def initialize ():

	kwargs = {'family': 'Helvetica', 'size': size, 'weight': 'bold'}

	global button
	global display
	global input

	if button == None:
		button  = tkFont.Font (**kwargs)

	if display == None:
		display = tkFont.Font (**kwargs)

	if input == None:
		input   = tkFont.Font (**kwargs)


def instances ():
	''' Return the active font instances. One could just refer to
	    the named font instances directly if one wanted to.
	'''

	return (button, display, input)
