import version
version.append ('$Revision: 91660 $')
del version

# This file is 'kImage' instead of 'Image' because of the potential
# conflict with the Python Imaging Library.

try:
	import Image
	import ImageColor
	import ImageDraw

except ImportError:
	import PIL.Image as Image
	import PIL.ImageColor as ImageColor
	import PIL.ImageDraw as ImageDraw

import ktl

import Color
import Images
import Stage


default_size = 18


class Simple:
	''' Base class for Image objects used within the GUI. This is not
	    subclassed from Image.Image, because the PIL objects do not
	    necessarily behave in an object-centric fashion.
	'''

	def __init__ (self, size=default_size, background='#ffffff'):

		# Base image for this object.
		self.base = None

		# 'Rendered' image for this object.
		self.image = None

		self.scale = 1
		self.background = None
		self.icon_size = None

		self.setBackground (background)
		self.setSize (size)



	def setBackground (self, color):

		changed = False

		if color == None:
			# Full transparency.
			color = (0, 0, 0, 0)
		else:
			color = ImageColor.getrgb (color)

			# Add transparency.
			color = (color[0], color[1], color[2], 0)


		if self.background != color:

			self.background = color
			changed = True

		return changed


	def setSize (self, size):

		changed = False

		icon_size = int (size)

		if self.icon_size != icon_size:
			self.icon_size = icon_size
			changed = True

		return changed


	def setScale (self, scale):

		changed = False

		scale = float (scale)

		if self.scale != scale:
			self.scale = scale
			changed = True

		return changed


	def setBase (self, image):

		changed = False

		if image != self.base:
			self.base = image
			changed = True

		return changed


	def redraw (self):
		''' Update our image content based on status changes.
		'''

		size = int (self.icon_size * self.scale)

		background = self.background

		new_image = Image.new ('RGBA', (size, size), background)

		# Image coordinate (0,0) is the upper-left corner.

		# The image being pasted is also specified as the mask,
		# the third argument to Image.paste (). This eliminates
		# unsightly black haloes around pasted images with alpha
		# channels. From the PIL documentation:

		#	Note that if you paste an "RGBA" image, the alpha
		#	band is ignored. You can work around this by using
		#	the same image as both source image and mask.

		if self.base != None:
			image = self.base.resize ((size, size), Image.ANTIALIAS)
			new_image.paste (image, (0, 0), image)

		self.image = new_image

		# Return the Image object for readability's sake,
		# though the original object can be referred to
		# directly.

		return new_image

# end of class Simple



class Path (Simple):

	def __init__ (self, size=default_size, background='#ffffff'):

		Simple.__init__ (self, size * 2, background)

		# If a Path image is transparent, it never blocks.
		#
		# If a Path image is lit, it is receiving light
		# from something further up the light path.
		#
		# If a Path image is blocking, it is in a state
		# such that elements further down the path will
		# not be lit.

		self.transparent = False
		self.blocking = False
		self.lit = False

		# Which image is displayed depends on the above
		# state bits.

		self.blocked = None
		self.passed = None


	def setSize (self, size):

		return Simple.setSize (self, size * 2)


	def setBlockingImage (self, image):

		changed = False

		if self.blocked != image:

			changed = True

			self.blocked = image

		return changed


	def setPassingImage (self, image):

		changed = False

		if self.passed != image:

			changed = True

			self.passed = image

		return changed


	def interpret (self, keyword=None, slice=None):
		''' Figure out whether this specific Path instance is
		    blocking light. Return None if there was no change;
		    return True if we are newly blocking light, return
		    False if we are newly passing light.
		'''

		if keyword == None or slice == None:
			suffix = None
			ascii = None
			binary = None

		else:
			suffix = keyword['name'][-3:]
			ascii  = slice['ascii']
			binary = slice['binary']

		blocking = None

		# For stages where we monitor the ordinal position
		# (filter wheels, for example), light is not (acceptably)
		# passing through a given stage if our position is not a
		# positive ordinal value (greater than zero).

		if suffix == 'ORD':
			value = binary

			if value < 1:
				if self.blocking == False:
					blocking = True

			elif self.blocking == True:
				blocking = False

		# Likewise, if a callback is registered for a NAM
		# keyword, assume that the positions 'Unknown' and
		# 'Home' are blocking light.

		elif suffix == 'NAM':
			value = ascii

			if value == 'unknown' or \
			   value == 'home'    or \
			   value == 'irregular':
				if self.blocking == False:
					blocking = True

			elif self.blocking == True:
				blocking = False

		# Inspect our current state and see whether our
		# base image should be changed.

		if self.lit == False:
			if self.base != None:
				self.base = None

		elif self.blocking == True and self.transparent == False:
			if self.base != self.blocked:
				self.base = self.blocked

		else:
			if self.base != self.passed:
				self.base = self.passed

		return blocking


# end of class Path



class Motion (Simple):

	def __init__ (self, size=default_size, background='#ffffff'):

		Simple.__init__ (self, size, background)

		# Which states will prompt the appearance of the
		# 'maintenance' icon rather than a pie chart?

		self.maintenance = ('calibrating', 'jogging', 'tracking', 'acquiring', 'slewing')

		# Helper data to render the pie-chart progress icon.

		self.pie	= True
		self.type	= None

		self.pie_image	= None

		# The following values are used to compute the completion
		# progress using REL and TRL keywords.

		self.progress	= None
		self.target	= None

		# The following value is used with a PCT keyword, which
		# eliminates the need for asynchronous computation of the
		# progress.

		self.completion = None


	def interpret (self, keyword=None, slice=None):

		if keyword == None or slice == None:
			return False

		suffix = keyword['name'][-3:]
		ascii  = slice['ascii']
		binary = slice['binary']

		changed = False

		if suffix == 'PCT':
			# Percentage completion of the move in progress.
			# PCT keyword is a fraction of 100, not a fraction
			# of 1. We want to use it later as a fraction of 1.

			self.completion = float (binary) / 100.0

		elif suffix == 'REL':
			# How far the stage has moved since the beginning
			# of this specific motion.

			self.progress = float (binary)

		elif suffix == 'TRL':
			# How far the stage is expected to move-- the
			# absolute difference between the position at
			# the start of the move, and the target position.

			self.target = float (binary)

		elif suffix == 'STA':
			ascii = ascii.lower ()

			if self.type != ascii:
				self.type = ascii

			if ascii != 'moving':
				self.completion	= None
				self.progress	= None
				self.target	= None

				if self.type in self.maintenance:
					changed = self.setBase (Images.get ('maintenance'))
				else:
					changed = self.setBase (None)


		if self.type == 'moving':
			if self.pie == True:
				# Two different conditions might be used to
				# prompt the creation of a progress image.
				# We are either receiving direct broadcasts
				# of the completion percentage, or we are
				# building our own notion of completion
				# based on multiple keywords.

				if self.completion != None or \
				   (self.progress  != None and self.target != None):
					new_image = self.buildImage ()
					changed = self.setBase (new_image)

			else:
				changed = self.setBase (Images.get ('maintenance'))

		return changed


	def buildImage (self, size=64, complete=Color.progress, pending='black'):
		''' Populate self.motion with a pie-chart progress icon
		    indicating the relative progress on the current move.

		    The 'complete' color is used to fill in the portion
		    of the move that is complete. The 'pending' color is
		    used to indicate the portion that is yet to come.
		'''

		if self.target == 0:
			# Not moving at all? Then you're already there.
			completion = 1

		elif self.progress != None and self.target != None:
			completion = abs (self.progress / self.target)

		elif self.completion != None:
			completion = self.completion

		else:
			# This should not occur.
			raise RuntimeError, 'not enough information to build a Motion pie icon'

		if completion > 1:
			# Probably the result of mixing REL and TRL
			# values from distinct move requests. If
			# REL and TRL are broadcast before STA,
			# this should never happen; but, if we got
			# here, it probably did.

			# Assert a sane value.

			completion = 1


		# Time to build an icon.

		background = ImageColor.getrgb (pending)
		complete   = ImageColor.getrgb (complete)
		pending	   = ImageColor.getrgb (pending)

		# Full background transparency.

		background = (background[0], background[1], background[2], 0)

		new_image = Image.new ('RGBA', (size, size), background)

		# Leave 5% on either side as a whitespace buffer surrounding
		# the actual progress indicator.

		diameter = int (size * 0.9)

		buffer = size - diameter

		if buffer < 1:
			buffer = 1

		bounding_box = (buffer, buffer, size - buffer, size - buffer)

		draw = ImageDraw.Draw (new_image)

		# For the pie slice, zero degrees is a line from the center
		# of the circle to the right-most edge (3 o'clock). We want
		# zero to be from the center to the top edge (12 o'clock).
		# Thus, apply an offset of 270 degrees.

		zero = 270

		angle = int (completion * 360)

		if angle == 360:
			# Full. Just draw a 'complete' circle, no pie slice.

			draw.ellipse (bounding_box,
				      outline='black', fill=complete)

		else:
			# Draw a 'pending' circle, with a slice
			# representing 'complete'.

			angle = (angle + zero) % 360

			draw.ellipse (bounding_box,
				      outline='black', fill=pending)

			draw.pieslice (bounding_box,
				       outline='black', fill=complete,
				       start=zero, end=angle)

		# Done building the image.

		return (new_image)


# end of class Motion



class Status (Simple):

	def __init__ (self, size=default_size, background='#ffffff'):

		Simple.__init__ (self, size, background)

		# Keep track of prior status information.

		self.results = {}
		self.state   = {}

		self.ok_values = ('ready', 'moving', 'ok', 'tracking')

		# Allow for per-Status image variation in whether
		# the motor is expected to remain powered after
		# a move.

		self.motor_hold = None


	def setMotorHold (self, hold):

		if hold != True and hold != False:
			raise ValueError, "the sole argument to setMotorHold is a boolean"

		changed = False

		if self.motor_hold != hold:

			self.motor_hold = hold
			changed = True

		return changed


	def interpret (self, keyword=None, slice=None):
		''' Update the local image components per the received
		    keyword.
		'''

		if keyword == None or slice == None:
			return False

		suffix = keyword['name'][-3:]
		ascii  = slice['ascii']
		binary = slice['binary']

		changed = False
		results = self.results
		state	= self.state

		if ascii != None:
			ascii = ascii.lower ()

		# Record relevant keywords for the generation of
		# the overall status icon.

		if suffix == 'ERR' or suffix == 'LIM' or suffix == 'MOE':
			state[suffix] = binary

		else:
			state[suffix] = ascii


		# That's it for processing the keyword values directly.
		# Build a status icon based on the contents of self.state.

		if 'LCK' in state:

			value = state['LCK']

			if value != 'unlocked' and value != '':

				status = Images.get ('locked')
			else:
				status = None

			results['LCK'] = status


		if 'ERR' in state:

			if state['ERR'] < 0:

				status = Images.get ('error')
			else:
				status = None

			results['ERR'] = status


		# 'Not in a limit' corresponds to binary value 0.
		# If we are in a limit, display it as a warning.

		if 'LIM' in state:

			if state['LIM'] != 0:

				status = Images.get ('warning')
			else:
				status = None

			results['LIM'] = status


		# If the stage is in a 'ready' state, confirm that the motor is
		# in the correct state.

		if 'MOO' in state and 'STA' in state:

			if 'MOE' in state:
				motor_hold = self.state['MOE']
			elif self.motor_hold != None:
				motor_hold = self.motor_hold
			else:
				motor_hold = Stage.servo_hold

			if state['STA'] == 'ready' and \
			   ((motor_hold == False and state['MOO'] == 'on') or \
			    (motor_hold == True  and state['MOO'] == 'off')):

				status = Images.get ('warning')
			else:
				status = None

			results['MOO'] = status

		# Consider the MOO keyword separately if it is not paired
		# with a STA keyword.

		elif 'MOO' in state:

			value = state['MOO']

			if 'MOE' in state:
				motor_hold = self.state['MOE']
			elif self.motor_hold != None:
				motor_hold = self.motor_hold
			else:
				motor_hold = Stage.servo_hold


			if motor_hold == False and value == 'on':
				status = Images.get ('warning')

			elif motor_hold == True and value == 'off':
				status = Images.get ('warning')

			else:
				status = None

			results['MOO'] = status


		# If the status keyword is not in an "acceptable" state, it
		# should be flagged as a warning, or critical.

		if 'STA' in state:

			value = state['STA']

			# The 'OK' values trump all other states, as they
			# imply everything is A-OK to request a move or
			# that the stage is otherwise operating in a
			# completely normal mode.

			if value in self.ok_values:
				status = Images.get ('ok')

			elif value == 'not calibrated':
				status = Images.get ('cant_proceed')

			elif value == 'fault'		or \
			     value == 'disabled':

				status = Images.get ('error')

			elif value == 'locked':
				status = Images.get ('locked')

			else:
				status = Images.get ('warning')

			results['STA'] = status


		if 'MSG' in state:

			if state['MSG'] != '':
				status = Images.get ('warning')
			else:
				status = None

			results['MSG'] = status


		if 'XMV' in state:

			if state['XMV'] != '':
				status = Images.get ('error')
			else:
				status = None

			results['XMV'] = status



		# Start off with results that should be prioritized,
		# or may depend on other results.

		if 'LCK' in results and results['LCK'] != None:
			status = results['LCK']

		elif 'ERR' in results and results['ERR'] != None:
			status = results['ERR']

		elif 'LIM' in results and results['LIM'] != None:

			if 'STA' in results and results['STA'] == Images.get ('error'):
				status = results['STA']
			else:
				status = results['LIM']

		elif 'MOO' in results and results['MOO'] != None:

			if 'STA' in results and results['STA'] == Images.get ('error'):
				status = results['STA']
			else:
				status = results['MOO']

		elif 'STA' in results and results['STA'] != None:
			status = results['STA']


		# Any states after this point are generally only rendered
		# for a 'standalone' Status image, one that is associated
		# with a single keyword.

		elif len (results) == 1:

			key = results.keys ()[0]
			status = results[key]

		else:
			# Insufficient state to build an image. We either
			# don't have enough broadcasts, or there are no
			# recognized (or actionable) suffixes associated
			# with this Status image.

			status = None


		self.results = results
		self.state   = state

		# After all those checks, did anything actually change?

		if self.base != status:
			self.base = status
			changed = True

		return changed


# end of class Status



class Temperature (Status):

	def __init__ (self, *arguments, **keyword_arguments):

		Status.__init__ (self, *arguments, **keyword_arguments)

		self.state = {}

		self.power = None
		self.setpoint = None


	def setPowerKeyword (self, keyword):

		if self.power == keyword:
			return False

		self.power = keyword

		return True


	def setSetpointKeyword (self, keyword):

		if self.setpoint == keyword:
			return False

		self.setpoint = keyword

		return True


	def interpret (self, keyword=None, slice=None):

		if keyword == None or slice == None:
			return False


		if keyword == self.power or keyword == self.setpoint:

			binary = slice['binary']
			self.state[keyword] = binary

		else:
			ktl.log (ktl.LOG_ERROR, "callback for %s not handled by Temperature image" % (keyword['name']))
			return False


		# Now analyze the current state, and select an
		# appropriate base image.

		base = None
		state = self.state


		if self.power in state and state[self.power] != True:

			base = None

		elif self.setpoint in state:
			setpoint = self.state[self.setpoint]

			if setpoint <= 0:
				base = Images.get ('bulb_off')
			else:
				base = Images.get ('bulb_on')


		if self.base != base:
			self.base = base
			return True
		else:
			return False


# end of class Temperature



class OmegaStatus (Status):

	def __init__ (self, *arguments, **keyword_arguments):

		Status.__init__ (self, *arguments, **keyword_arguments)

		self.button = None
		self.service = None
		self.power = None

		# Omega keywords this object understands, and will attempt
		# to monitor when self.setService () is called.

		self.known = ('DISPSTA', 'SETPOINT', 'TEMP')


	def setButton (self, button):

		if self.button == button:
			return False

		self.button = button

		return True


	def setPowerKeyword (self, keyword):

		if self.power == keyword:
			return False

		self.power = keyword

		return True


	def setService (self, service):

		if self.service == service:
			return False

		if self.button == None:
			raise RuntimeError, "you must call OmegaStatus.setButton first"

		self.service = service

		for keyword in self.known:
			if keyword in service:
				self.button.setStatusKeyword (service[keyword])

		return True


	def interpret (self, keyword=None, slice=None):

		if keyword == None or slice == None:
			return False


		if keyword == self.power:

			self.state[self.power] = slice['binary']

		else:
			name = keyword['name']

			if name in self.known:
				self.state[name] = slice['ascii'].lower ()
			else:
				ktl.log (ktl.LOG_ERROR, "callback for %s not handled by OmegaStatus image" % (name))
				return False


		# Now analyze the current state, and select an
		# appropriate base image.

		base = None
		state = self.state


		if self.power in state and state[self.power] != True:

			base = Images.get ('error')

		elif 'DISPSTA' in state and state['DISPSTA'] != 'ready':

			base = Images.get ('error')

		elif 'SETPOINT' in state and 'TEMP' in state:

			setpoint = float (state['SETPOINT'])
			temp	 = float (state['TEMP'])

			if setpoint == 0:
				base = Images.get ('ok')

			elif temp > (setpoint + 5):
				base = Images.get ('warning')

			else:
				base = Images.get ('ok')

		else:
			base = Images.get ('ok')


		if self.base != base:
			self.base = base
			return True
		else:
			return False


# end of class OmegaStatus
