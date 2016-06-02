import version
version.append ('$Revision: 90125 $')
del version


try:
	import Image
	import ImageTk

except ImportError:
	import PIL.Image   as Image
	import PIL.ImageTk as ImageTk

import ktl
import Tkinter

import Color
import Event
import Font
import Images
import kImage
import Log
import Monitor
# Can't import Popup here, doing so results in an import loop.


class Simple (Tkinter.Button):

	def __init__ (self, master, main, foreground='black', background='white', initialize=True, fontsized=False, image=True):

		''' Create an empty Tk.Button with all of the machinery
		    we expect to use. The default is populated with an
		    image.
		'''

		self.keyword = None
		self.service = None

		Tkinter.Button.__init__ (self,
					master = master,
					anchor = Tkinter.W,
					foreground = foreground,
					background = background,
					activebackground = Color.highlight,
					borderwidth = 1,
					font = Font.button,
					relief = Tkinter.RAISED,
					cursor = 'hand2',
					padx = 0,
					pady = 0)

		# Flags that change the internal behavior of the button.

		self.hidden    = False
		self.online    = True
		self.highlight = False
		self.fontsized = fontsized
		self.icon_size = None
		self.image_pil = None

		# Where the main window is.

		self.main = main

		# What happens when the button gets depressed.

		self['command'] = self.command


		if fontsized == True or fontsized == False:
			self.setSize ()
		else:
			raise ValueError, 'fontsized argument must be a boolean'

		if image == True:
			self.image_pil = kImage.Simple (size=self.icon_size)
			self.image_tk  = ''

			# Default starter image: empty.

			if initialize == True:
				self.setImage (None)
				self.redraw ()


	def setKeyword (self, keyword, callback=True):

		if self.keyword == keyword:
			return False

		self.keyword = keyword

		self.setService (keyword['service'])

		if callback == True:
			self.setCallback (keyword)

		return True


	def setCallback (self, keyword):
		''' Set up this Button object to receive callbacks
		    from the specified ktl.Keyword instance. setCallback()
		    will also establish monitoring of the ktl.Keyword
		    if necessary.
		'''

		keyword.callback (self.receiveCallback)

		if keyword['monitored'] == True:
			self.receiveCallback (keyword)
		else:
			Monitor.queue (keyword)


	def setService (self, service):
		''' Retain a ktl.Service object for later reference. Note
		    that if setKeyword() is invoked, the object retained
		    by a Simple instance will be updated to match.
		'''

		changed = False

		if isinstance (service, ktl.Service):
			pass
		else:
			service = self.main.services[service]

		if self.service != service:
			self.service = service
			changed = True

		return changed


	def setImage (self, image):

		return self.image_pil.setBase (image)


	def setScale (self, scale):
		''' Floating point factor used to scale the size of
		    the component image; for example, if the icon_size
		    is 16 and the scale is 0.5, the resulting image
		    will be 8 pixels on either side.
		'''

		return self.image_pil.setScale (scale)


	def setSize (self, size=None):
		''' Check the Main.Window instance for any size updates,
		    and update our local image size as appropriate.
		'''

		changed = False

		if self.fontsized == False and hasattr (self.main, 'icon_size'):
			icon_size = self.main.icon_size

		elif self.fontsized == True:
			icon_size = Font.display.cget ('size')

		else:
			icon_size = kImage.default_size


		if icon_size != None and icon_size != self.icon_size:

		   	self.icon_size = icon_size

			if hasattr (self.image_pil, 'setSize'):
				self.image_pil.setSize (self.icon_size)

			changed = True

		return changed


	def redraw (self):

		# Always build an image, even if there is no
		# image to display. The resulting image will
		# be the correct size, but fully transparent.
		# This is preferable to no image at all, since
		# that would have a different visible size,
		# which could prompt the grid to shift.
		#
		# Otherwise, we could just set self.image_tk to ''.

		image = self.image_pil.redraw ()

		self.image_tk = ImageTk.PhotoImage (image)

		Event.tkSet (self, 'image', self.image_tk)


	def command (self, *ignored):
		''' Invoked whenever a Simple button is pressed.
		'''

		pass


	def receiveCallback (self, keyword):
		''' Accepts a ktl.Keyword object, and queues an
		    update request based on the new value.

		    This is expected to be used in conjunction
		    with ktl.Keyword.callback() and ktl.Keyword.monitor().
		'''

		if keyword['populated'] == False:
			return

		try:
			keyword['ascii']
		except:
			return


		slice = keyword['history'][-1]

		Event.queue (self.update, keyword, slice)


	def update (self, *arguments, **keyword_arguments):

		changed = self.interpret (*arguments, **keyword_arguments)

		if changed == True:
			self.redraw ()


	def interpret (self, *ignored):
		''' Process an update to the Simple button.
		'''

		changed = self.setSize ()

		return changed


	def hide (self, hide=True):
		''' It is possible that sub-classes may want take
		    specific actions when a button is hidden beyond
		    grid manipulations.
		'''

		if self.hidden == hide:
			return

		if hide == True:
			self.grid_remove ()

		elif hide == False:
			# Assume a previous invocation of grid()
			# set appropriate values.
			self.grid ()

		else:
			raise ValueError, 'argument to hide() must be True or False'

		self.hidden = hide


	def reveal (self):

		self.hide (False)


	def connect (self):
		''' Enable direct (non-broadcast) keyword activity.
		'''

		if self.online == True:
			return

		self.online = True

		self.enableActivity ()


	def disconnect (self):
		''' Disable any direct (non-broadcast) keyword activity
		    until further notice.
		'''

		if self.online == False:
			return

		self.online = False

		self.disableActivity ()


	def enableActivity (self):

		Event.tkSet (self, 'state', Tkinter.NORMAL)
		Event.tkSet (self, 'cursor', 'hand2')

		# Restore the 'raised' look, if necessary.

		if self.highlight == True:
			Event.tkSet (self, 'relief', Tkinter.RAISED)


	def disableActivity (self):

		Event.tkSet (self, 'state', Tkinter.DISABLED)
		Event.tkSet (self, 'cursor', '')

		# Remove the 'raised' look, if necessary,
		# without forgetting that we want to restore
		# the 'raised' look when activity is re-enabled.

		if self.highlight == True:
			Event.tkSet (self, 'relief', Tkinter.FLAT)


	def bindHighlight (self):
		''' This function is invoked by Button objects associated
		    with InfoBox objects. See BoxButton for a simple example.
		'''

		if hasattr (self, 'box'):
			pass
		else:
			return

		# Continue highlighting the image if the cursor
		# passes from the background frame to the button.

		self.bind ('<Enter>', self.box.createHighlight)
		self.bind ('<Leave>', self.box.removeHighlight)


	def createHighlight (self):

		if self.highlight == True:
			return

		self.highlight = True

		if self['state'] != Tkinter.NORMAL:
			return

		Event.tkSet (self, 'relief', Tkinter.RAISED)


	def removeHighlight (self):

		if self.highlight == False:
			return

		self.highlight = False

		Event.tkSet (self, 'relief', Tkinter.FLAT)


# end of class Simple



class Text (Simple):

	def __init__ (self, master, main, background='white'):

		Simple.__init__ (self, master=master, main=main, background=background, image=False)

		self.image_pil = None
		self.image_tk = None

		self['anchor'] = Tkinter.CENTER

		self['padx'] = 2
		self['pady'] = 2


	def setImage (self, image, force_update=False):

		raise NotImplementedError, "Text buttons don't have images"


	def redraw (self):

		pass


	def update (self, keyword=None, slice=None):

		if slice != None:
			Event.tkSet (self, 'text', slice['ascii'])


# end of class Text



class Increment (Simple):
	''' Expected to be used with a relative keyword, as opposed to
	    computing an increment based on the present value of the
	    keyword.
	'''

	def __init__ (self, master, main, background='#ffffff'):

		Simple.__init__ (self, master=master, main=main, foreground='light grey', background=background)

		Event.tkSet (self, 'activebackground', Color.selection)

		# Arbitrary default value for incrementing.

		self.increment = 10


	def setIncrement (self, increment):

		changed = False

		if self.increment != increment:

			self.increment = increment
			changed = True

		return changed


	def command (self, *ignored):

		if self.keyword == None:
			raise RuntimeError, 'no keyword associated with Increment button'

		self.keyword.write (self.increment, wait=False)


# end of class Increment



class Jogger (Simple):

	''' When a button gets pushed, start jogging. This implies
	    setting the mode (if necessary), and setting the speed.
	'''

	def __init__ (self, *arguments, **keyword_arguments):

		Simple.__init__ (self, *arguments, **keyword_arguments)

		Event.tkSet (self, 'activebackground', Color.selection)

		self.mode_keyword = None
		self.jog_keyword = None

		self.jog_mode = 'Jog'
		self.jog_speed = None


	def setModeKeyword (self, keyword):

		self.mode_keyword = keyword
		return True

	def setJogKeyword (self, keyword):

		self.jog_keyword = keyword
		return True

	def setJogMode (self, mode):

		self.jog_mode = mode
		return True

	def setJogSpeed (self, speed):

		self.jog_speed = speed
		return True


	def command (self, *ignored):

		mode = self.mode_keyword
		jogger = self.jog_keyword

		if mode == None:
			raise RuntimeError, 'Jogger button has no mode Keyword'

		if jogger == None:
			raise RuntimeError, 'Jogger button has no jog Keyword'

		if self.jog_speed == None:
			raise RuntimeError, 'Jogger button speed is not set'


		if mode['populated'] == True and mode['monitored'] == True:
			current_mode = mode['ascii']
		else:
			current_mode = mode.read ()

		current_mode = current_mode.lower ()


		if current_mode != self.jog_mode.lower ():
			# Need to perform a blocking write here to ensure
			# that the mode is correctly set before trying to
			# set the jog speed.

			mode.write (self.jog_mode, wait=True)


		# No need to wait when setting the speed.
		jogger.write (self.jog_speed, wait=False)


# end of class Jogger





#
# #
# The next set of buttons expect a tight association with an InfoBox.
# #
#


class InfoBox (Simple):

	def __init__ (self, box, initialize=True):
		''' 'box' is the InfoBox that we are a member of.
		'''

		self.box = box

		main = box.main

		Simple.__init__ (self, main.frame, main, initialize=initialize)

		# Default rendering of an InfoBox button should be flat.
		# It will be modified by calls to createHighlight()
		# and removeHighlight().

		Event.tkSet (self, 'relief', Tkinter.FLAT)

		self.bindHighlight ()


# end of class InfoBox



class Bulb (InfoBox):

	def __init__ (self, box):

		InfoBox.__init__ (self, box)

		self.inverted = False
		self.active = False

		self.off_image = 'bulb_off'
		self.on_image = 'bulb_on'
		self.off_value = 'off'
		self.on_value = 'on'
		self.verb = 'Turning'

		if box != None:
			self.label = box.label['text']
			self.label = self.label.split ('\n')[0].strip ()

			if self.label == '':
				self.label == 'lamp'
		else:
			self.label = 'lamp'


		Event.tkSet (self, 'activebackground', Color.selection)

		self.setImage (Images.get (self.off_image))
		self.redraw ()

		self.bind ('<Enter>', self.startMouseover)
		self.bind ('<Leave>', self.stopMouseover)



	def command (self):
		''' Invoked whenever a Bulb button is pressed.
		'''

		if self.active == True:
			value = self.off_value
		else:
			value = self.on_value

		if self.keyword == None:
			raise RuntimeError, 'no keyword associated with Bulb button'


		message = "%s %s %s..." % (self.verb, value, self.label)

		try:
			self.keyword.write (value, wait=False)
		except:
			message = "Unable to toggle %s" % (self.label)

		Log.alert (message)


	def startMouseover (self, *ignored):
		''' Invoked when a mouseover begins. Note that we explicitly
		    invoke InfoBox.createHighlight(), since Tkinter appears
		    to have issues with multiple functions binding to the same
		    event.
		'''

		self.inverted = True
		self.update ()

		if hasattr (self, 'box') and self.box != None:
			self.box.createHighlight ()


	def stopMouseover (self, *ignored):
		''' Invoked when a mouseover ends. Note that we explicitly
		    invoke InfoBox.removeHighlight(), since Tkinter appears
		    to have issues with multiple functions binding to the same
		    event.
		'''

		self.inverted = False
		self.update ()

		if hasattr (self, 'box') and self.box != None:
			self.box.createHighlight ()


	def interpret (self, keyword=None, slice=None):

		changed = self.setSize ()

		if slice == None:
			pass
		else:
			binary = slice['binary']

			if binary == 0 or binary == False:
				self.active = False
			elif binary == 1 or binary == True:
				self.active = True
			else:
				self.active = 'unknown'


		if self.active == False and self.inverted == False:
			image = Images.get (self.off_image)

		elif self.active == False and self.inverted == True:
			image = Images.get (self.on_image)

		elif self.active == True and self.inverted == False:
			image = Images.get (self.on_image)

		elif self.active == True and self.inverted == True:
			image = Images.get (self.off_image)

		elif self.active == False:
			image = Images.get (self.off_image)

		else:
			image = Images.get ('unknown')

		new_image = self.setImage (image)

		if new_image == True:
			changed = True

		return changed


# end of class Bulb



class Ordinal (Text):

	def __init__ (self, box):

		self.box = box

		main = box.main

		Text.__init__ (self, main.frame, main)

		Event.tkSet (self, 'text', 'Modify...')

		# Keep track of any popup window we've invoked,
		# so that it is destroyed on repeat button-presses.

		self.popped = None

		# Default rendering of an Ordinal button should be flat.
		# It will be modified by calls to createHighlight()
		# and removeHighlight().

		Event.tkSet (self, 'relief', Tkinter.FLAT)

		self.bindHighlight ()


	def command (self, *ignored):

		if self.box.stage == None:
			raise RuntimeError, "no stage set for OrdinalBox"


		if self.popped != None:
			self.popped.destroy ()

		import Popup
		self.popped = Popup.Ordinal (self, self.service)


	def update (self, *arguments, **keyword_arguments):

		Text.update (self, *arguments, **keyword_arguments)

		if self.popped != None:
			self.popped.update ()


# end of class Ordinal



class Status (InfoBox):

	def __init__ (self, box, wide=None, tall=None):

		self.wide = False
		self.tall = False

		if wide == None and tall == None:
			self.wide = True

		elif wide == True and tall == True:
			raise ValueError, "a Status button must be wide or tall, not both"

		elif wide == True:
			self.wide = True

		elif tall == True:
			self.tall = True

		else:
			raise ValueError, "unhandled wide/tall values: %s/%s" % (wide, tall)

		# Component images.

		self.motion = kImage.Motion ()
		self.status = kImage.Status ()


		InfoBox.__init__ (self, box, False)

		# Now that all of the necessary machinery is in place,
		# create an initial, blank image.

		self.buildImage ()
		self.redraw ()

		# Keep track of any popup window we've invoked,
		# so that it is destroyed on repeat button-presses.

		import Popup
		self.popup_class = Popup.Detail
		self.popped = None

		self.motor_hold = None


	def setMotorHold (self, hold):

		# Don't try to catch exceptions about setMotorHold()
		# not being present; its absence here is indicative of
		# a programming error.

		changed = self.status.setMotorHold (hold)

		if changed == True:
			self.motor_hold = hold

		return changed


	def setPopup (self, popup):
		''' Change the popup class invoked when the button
		    is depressed. The default is GUI.Popup.Detail.
		'''

		changed = False

		if self.popup_class != popup:

			self.popup_class = popup
			changed = True

		return changed


	def pie (self, enable=True):

		if isinstance (enable, bool):
			pass
		else:
			raise ValueError, "argument to pie() is not a boolean: %s" % (enable)

		self.motion.pie = False


	def command (self, *ignored):
		''' Invoked whenever a Status button is pressed.
		'''

		label = self.box.label.get ()

		label = label.split ('\n')[0]
		label = label.split ('(')[0]
		label = label.strip ()

		import Popup
		if self.box.stage == None and self.popup_class == Popup.Detail:
			Log.error ('Status button depressed for stage that has no notion of which stage it is.')
			Log.error ('This particular Status button is affiliated with the InfoBox labelled:')
			Log.error ("	%s" % (label))

			return


		# Destroy the old popup, if any.

		if self.popped != None:
			self.popped.destroy ()


		# Invoke a new one.

		self.popped = self.popup_class (self, self.service)

		self.popped.title ("%s detail view" % (label))


	def redraw (self):

		# The resized and merged image is stored with the default
		# kImage.Simple instance associated with the parent Simple
		# class. It is assigned via self.setImage() at the end of
		# self.buildImage().

		image = self.image_pil.base

		self.image_tk = ImageTk.PhotoImage (image)

		Event.tkSet (self, 'image', self.image_tk)


	def interpret (self, keyword=None, slice=None):

		changed = False

		# Check for size changes before building a new image.

		changed = self.setSize ()

		if changed == True:

			self.motion.setSize (self.icon_size)
			self.status.setSize (self.icon_size)

			# Pass along the message of an icon size change
			# to the Popup.Detail, if any.

			if self.popped != None:
				self.popped.update ()


		if keyword != None:
			motion = self.motion.interpret (keyword, slice)
			status = self.status.interpret (keyword, slice)

			if motion == True or status == True:
				changed = True

		if changed == True:
			self.buildImage ()

		return changed


	def buildImage (self):
		''' Merge the two icons into a single PIL Image.

		    If 'wide' is set to True for the Status button, the
		    'motion' and 'status' icons will be stacked horizontally,
		    with the motion icon on the left.

		    In ASCII art:

		    /---|---\
		    |mot|sta|
		    \---|---/

		    If 'tall' is set to True, the icons will be stacked
		    vertically, with the status icon on the bottom.

		    In ASCII art:

		    /---\
		    |mot|
		    -----
		    |sta|
		    \---/
		'''

		# Acquire the background color from a component image.

		background = self.motion.background

		size = self.icon_size


		if self.wide == True and self.tall == True:
			raise RuntimeError, "both wide and tall are True; this can't happen"

		if self.wide == True:
			new_image = Image.new ('RGBA', (size * 2, size), background)

			motion_coords = (0, 0)
			status_coords = (size, 0)

		elif self.tall == True:
			new_image = Image.new ('RGBA', (size, size * 2), background)

			motion_coords = (0, 0)
			status_coords = (0, size)

		else:
			raise RuntimeError, "neither wide or tall are True; this can't happen"


		if self.motion.base != None:
			motion = self.motion.base.resize ((size, size), Image.ANTIALIAS)
			new_image.paste (motion, motion_coords, motion)

		if self.status.base != None:
			status = self.status.base.resize ((size, size), Image.ANTIALIAS)
			new_image.paste (status, status_coords, status)


		self.setImage (new_image)


	def connect (self):
		''' Enable direct (non-broadcast) keyword activity.
		'''

		Simple.connect (self)

		if self.popped != None:
			self.popped.connect ()


	def disconnect (self):
		''' Disable any direct (non-broadcast) keyword activity
		    until further notice.
		'''

		Simple.disconnect (self)

		if self.popped != None:
			self.popped.disconnect ()


# end of class Status



class Path (Status):

	def __init__ (self, box):

		# Additional component image.

		self.path = kImage.Path ()

		Status.__init__ (self, box)

		# Keep track of the next element(s) in the light path.

		self.next = []


	def setNext (self, next):
		''' Assign another Path button as the next object
		    in the light path.
		'''

		if isinstance (next, str):
			raise TypeError, 'next object in light path must resemble a Path button'

		if hasattr (next, '__iter__'):
			items = next
		else:
			items = (next,)

		for next in items:
			if hasattr (next, 'light') and callable (next.light):
				pass
			else:
				raise RuntimeError, 'next object in light path must resemble a Path button'

			self.next.append (next)


	def light (self, lit=True):
		''' Indicate whether this Path button is receiving light
		    (lit == True) or is dark (lit == False).
		'''

		# Any changes in self.path.blocking are handled
		# in self.block(), so we will only concern ourselves
		# with propagating our 'lit' status.

		changed = False
		next = False

		if self.path.lit != lit:

			self.path.lit = lit
			changed = True

			if self.path.blocking == False	 or \
			   self.path.transparent == True or \
			   self.hidden == True:

				next = True

		if changed == True:
			self.path.interpret ()
			self.buildImage ()
			self.redraw ()

			if next == True:
				for next in self.next:
					next.light (lit)


	def block (self, blocking=True):
		''' Indicate whether this Path button blocking or passing
		    light.
		'''

		# Any changes in self.path.lit are handled
		# in self.light(), so we will only concern ourselves
		# with changes to our 'blocking' status.

		changed = False

		if self.path.blocking != blocking:

			self.path.blocking = blocking

			# A change in blocking status is only relevant if
			# this element is lit. It is not possible for our
			# status to change if the element is transparent,
			# or hidden.

			if self.path.lit == True	  and \
			   self.path.transparent == False and \
			   self.hidden == False:

				changed = True


		if changed == True:
			self.path.interpret ()
			self.buildImage ()
			self.redraw ()

			# Propagate any changes to the lightedness of
			# elements further on in the light path.

			if self.path.blocking == True:
				next_is_lit = False
			else:
				next_is_lit = True

			for next in self.next:
				next.light (next_is_lit)


	def hide (self, hide=True):

		Status.hide (self, hide)

		if self.path.lit == False      or \
		   self.path.blocking == False or \
		   self.path.transparent == True:

			 # No additional inspection necessary.
			return

		if self.hidden == True:

			# We used to be blocking, but now we're
			# effectively transparent.

			for next in self.next:
				next.light (True)

		else:

			# We used to be effectively transparent,
			# but now we're blocking.

			for next in self.next:
				next.light (False)


	def interpret (self, keyword=None, slice=None):

		changed = self.setSize ()

		if changed == True:

			self.motion.setSize (self.icon_size)
			self.path.setSize   (self.icon_size)
			self.status.setSize (self.icon_size)


		path = None

		if keyword != None:

			motion = self.motion.interpret (keyword, slice)
			path   = self.path.interpret   (keyword, slice)
			status = self.status.interpret (keyword, slice)

			if motion == True or status == True:
				changed = True

			# Additional intelligence is required if the
			# path element changes, because we must propagate
			# the change. The PathImage.interpret() method
			# will return None if there was no change.

			if path != None:

				changed = True
				self.block (path)


		if changed == True and path == None:
			# If invoked above, self.block() invokes
			# self.buildImage() directly. Thus, we only
			# need to invoke self.buildImage() separately
			# if path == None.

			self.buildImage ()

		return changed


	def buildImage (self):
		''' Merge the three icons into a single PIL Image, and update
		    the local display.

		    The path image will occupy two-thirds of the image on
		    the left side, with the motion and status images stacked
		    on top of each other on the right side.

		    In ASCII art:

		    /---|---|---\
		    |       |mot|
		    - path  +----
		    |       |sta|
		    \---|---|---/
		'''

		# Acquire the background color from a component image.

		background = self.motion.background

		size = self.icon_size


		new_image = Image.new ('RGBA', (size * 3, size * 2), background)

		motion_coords = (size * 2, 0)
		path_coords   = (0, 0)
		status_coords = (size * 2, size)


		if self.motion.base != None:
			motion = self.motion.base.resize ((size, size), Image.ANTIALIAS)
			new_image.paste (motion, motion_coords, motion)

		if self.path.base != None:
			path = self.path.base.resize ((size * 2, size * 2), Image.ANTIALIAS)
			new_image.paste (path, path_coords, path)

		if self.status.base != None:
			status = self.status.base.resize ((size, size), Image.ANTIALIAS)
			new_image.paste (status, status_coords, status)


		self.setImage (new_image)


# end of class Path



class Temperature (Status):
	''' Use two kImage.Simple instances to reflect the overall state
	    of a temperature-controlled system.

	    One image is dedicated to whether the temperature control
	    is active (kImage.Temperature), signified with a light bulb
	    that is on or off. The second image reflects the state of
	    the controller: powered up, connected, etc.
	'''

	def __init__ (self, *arguments, **keyword_arguments):

		Status.__init__ (self, *arguments, **keyword_arguments)

		# We want to use different component images for this button.

		self.motion = kImage.Temperature ()
		self.status = kImage.OmegaStatus ()

		if hasattr (self.status, 'setButton'):
			self.status.setButton (self)

		# Redraw.

		self.buildImage ()
		self.redraw ()

		import Popup
		self.popup_class = Popup.Omega

		# Lists to dictate which sub-image will be used to interpret
		# a broadcast for a given ktl.Keyword object.

		self.motion_keywords = []
		self.status_keywords = []

		self.power = None


	def setPowerKeyword (self, keyword, callback=True):

		if self.power == keyword:
			return False

		self.power = keyword

		self.setMotionKeyword (keyword, callback=False)
		self.setStatusKeyword (keyword, callback=False)

		self.motion.setPowerKeyword (keyword)
		self.status.setPowerKeyword (keyword)

		if callback == True:
			self.setCallback (keyword)

		return True


	def setMotionKeyword (self, keyword, callback=True):

		if keyword in self.motion_keywords:
			return False

		self.motion_keywords.append (keyword)

		if callback == True:
			self.setCallback (keyword)

		return True


	def setStatusKeyword (self, keyword, callback=True):

		if keyword in self.status_keywords:
			return False

		self.status_keywords.append (keyword)

		if callback == True:
			self.setCallback (keyword)

		return True


	def interpret (self, keyword=None, slice=None):

		# Use Simple.interpret() to pick up size changes.
		# There are a few Status button operations that must then
		# be invoked manually.

		changed = Simple.interpret (self)

		if changed == True:

			self.motion.setSize (self.icon_size)
			self.status.setSize (self.icon_size)

			if self.popped != None:
				self.popped.update ()

		if keyword == None or slice == None:

			if changed == True:
				self.buildImage ()

			return changed


		status = False

		if keyword in self.status_keywords:
			status = self.status.interpret (keyword, slice)

			if status == True:
				changed = True

		if keyword in self.motion_keywords:
			motion = self.motion.interpret (keyword, slice)

			if motion == True:
				changed = True

		if changed == True:
			self.buildImage ()

		return changed


	def setService (self, service):

		if hasattr (self.status, 'setService'):
			self.status.setService (service)

		return Status.setService (self, service)


# end of class Temperature
