import version
version.append ('$Revision: 90315 $')
del version


import ktl
import Tkinter
from Tkinter import N, E, S, W
import sys
import traceback

import Button
import Color
import Event
import Font
import Images
import kImage
import Log
import Monitor
import Stage


def sortStringAsNumber (number1, number2):

	if number1 == number2:
		return 0

	# It's possible that this function will get called with 'None'
	# as an argument. If a 'None' value is present, consider that
	# a trump card, asserting None is the smallest value possible.

	if number1 == 'None':
		return -1

	if number2 == 'None':
		return 1

	number1 = float (number1)
	number2 = float (number2)

	if number1 > number2:
		return 1

	if number1 < number2:
		return -1

	# The first equality check may not necessarily catch all
	# equalities. If we made it this far, though, equality
	# is fairly-well assured.

	return 0



def validateFloat (value, range=None):
	''' Assert that value is a valid floating point number, within
	    the given range range (dictionary with keys 'minimum' and
	    'maximum'). If it is not, raise ValueError.
	'''

	if isinstance (value, str):
		pass
	else:
		raise RuntimeError, 'validateFloat() only operates on strings'


	# The cast will raise ValueError if it is not a valid floating
	# point value.

	value = float (value)

	if range != None:
		minimum = range['minimum']
		maximum = range['maximum']

		if minimum != None:
			minimum = float (minimum)
			if value < minimum:
				raise ValueError, "%f exceeds minimum %f" % (value, minimum)

		if maximum != None:
			maximum = float (maximum)
			if value > maximum:
				raise ValueError, "%f exceeds maximum %f" % (value, maximum)



def validateInteger (value, range=None):
	''' Assert that value is a valid integer, within the given
	    range (dictionary with keys 'minimum' and 'maximum').
	    If it is not, raise ValueError.
	'''

	if isinstance (value, str):
		pass
	else:
		raise RuntimeError, 'validateInteger() only operates on strings'


	# The cast will raise ValueError if it is not a valid integer.
	# This includes conversion of floating point strings, such as
	# '24.0' to integer form.

	value = int (value)

	if range != None:

		minimum = range['minimum']
		maximum = range['maximum']

		if minimum != None:
			minimum = int (minimum)
			if value < minimum:
				raise ValueError, "%d exceeds minimum %d" % (value, minimum)

		if maximum != None:
			maximum = int (maximum)
			if value > maximum:
				raise ValueError, "%d exceeds maximum %d" % (value, maximum)



class ColorLabel (Tkinter.Label):

	def __init__ (self,
		      master = None,
		      text = '--',
		      anchor = Tkinter.W,
		      foreground = '#000000',
		      background = '#000000',
		      justify = Tkinter.LEFT,
		      padx = 0,
		      pady = 0):

		Tkinter.Label.__init__ (self,
					master = master,
					anchor = anchor,
					foreground = foreground,
					background = background,
					font = Font.display,
					justify = justify,
					padx = padx,
					pady = pady,
					text = text)


	def set (self, value):

		return Event.tkSet (self, 'text', value)


	def get (self):

		# Don't catch TclError exceptions here, since this is a
		# problem the caller really wants to be aware of.

		return self['text']

# end of class ColorLabel



class WhiteLabel (ColorLabel):

	def __init__ (self, master, text='--'):

		ColorLabel.__init__ (self, master = master,
					  text = text,
					  background = Color.white,
					  anchor = Tkinter.E)

# end of class WhiteLabel



class Value (Tkinter.Frame):
	''' A basic Frame class that contains a displayed text element
	    and a "go" button if the value is changed by the user.
	'''

	def __init__ (self, master,
			box	    = None,
			main	    = None,
			top	    = None,
			go	    = True,
			anchor	    = Tkinter.W,
			background  = Color.white,
			foreground  = Color.value,
			borderwidth = 0,
			justify	    = Tkinter.LEFT,
			display	    = None,
			arguments   = {},
			text	    = '--'):

		Tkinter.Frame.__init__ (self, master,
					background  = background,
					borderwidth = borderwidth,
					relief	    = Tkinter.FLAT)

		if main != None:
			self.main = main
		elif hasattr (master, 'MainWindow'):
			self.main = master
		elif hasattr (box, 'MainWindow'):
			self.main = box
		elif hasattr (box, 'main') and hasattr (box.main, 'MainWindow'):
			self.main = box.main
		else:
			self.main = None

		if self.main != None:
			self.icon_size = self.main.icon_size
		else:
			self.icon_size = kImage.default_size

		if top != None:
			self.top = top
		else:
			if self.main != None:
				self.top = self.main.top
			else:
				self.top = None

		if box != None:
			self.label = box.label['text']
			self.label = self.label.split ('\n')[0]

			self.box = box
		else:
			self.label = None
			self.box   = None

		self.grid (sticky=N+E+S+W)

		self.background = background
		self.foreground = foreground

		# Did the user select a new value?

		self.choice = None

		# Should the user's choice clear when the go button
		# is activated? Manipulated via self.setKeepChoice().

		self.keep_choice = False

		# Is the choice valid? If self.validator (expected to be
		# a function accepting a value as its sole argument) is None,
		# no validation will take place. The validator should raise
		# ValueError exceptions if the value is invalid.

		self.validator = None
		self.valid = True

		# What is the "real" value, as known by the keyword?

		self.value = None
		self.keyword = None

		# Is something overriding the display?

		self.override = None

		# Are we connected to our KTL service?

		self.online = True

		# Is this Value object completely disabled?

		self.enabled = True

		# Should we try to put messages up on the menu when the
		# user writes a value?

		self.messages = True

		# If an element is passed in to use for the value display
		# (such as a menu, or an entry box), use that. Otherwise,
		# create a Tkinter.Label to use as a read-only display.

		if display != None:
			self.display = display (**arguments)
		else:
			self.display = Tkinter.Label (self,
						anchor=anchor,
						foreground=foreground,
						background=background,
						font=Font.display,
						justify=justify,
						text=text)

			# Labels don't interact.

			self.online = False
			self.enabled = False


		# Image used for the "go" button.

		if go == True:

			self.go_button = Button.Simple (self, self.main)
			self.go_button['command'] = self.write

			# Properly adjust the state of the "go" button before
			# gridding it for display.

			self.checkGoButton ()


		self.display.grid (row=0, column=0, sticky=N+E+S)

		if go == True:
			self.go_button.grid (row=0, column=1, sticky=W)


	def checkGoButton (self, background='#ffffff'):
		''' Create an ImageTk instance for the "go" button
		    that is "active" if a user has selected a value,
		    but blank otherwise.

		    Also, disable the button if there is no active
		    choice, or if the choice is invalid.
		'''

		# If there is a writable choice, build a "go" button.

		if self.choice != None	and \
		   self.choice != ''	and \
		   self.valid  == True	and \
		   self.online == True	and \
		   self.enabled == True:

			image  = Images.get ('apply')
			cursor = 'hand2'
			relief = Tkinter.RAISED
			state  = Tkinter.NORMAL

			highlight = Color.highlight

		else:
			image  = None
			cursor = ''
			relief = Tkinter.FLAT
			state  = Tkinter.DISABLED

			highlight = Color.white


		# Update the display accordingly.

		changed = self.go_button.setImage (image)

		if changed == True:
			self.go_button.redraw ()

		Event.tkSet (self.go_button, 'cursor', cursor)
		Event.tkSet (self.go_button, 'state',	state)
		Event.tkSet (self.go_button, 'relief', relief)
		Event.tkSet (self.go_button, 'highlightbackground', highlight)


	def receiveCallback (self, keyword):
		''' Accepts a ktl.Keyword object, and updates our
		    our internal record of the Keyword value.

		    This is expected to be used in conjunction
		    with Keyword.callback() and Keyword.monitor().

		    Sub-classes will likely need to over-ride this
		    method. Care should be exercised to always use
		    Event.queue for anything that modifies the display,
		    due to Tk's single-threaded processing of GUI events.
		'''

		if keyword['populated'] == False:
			return

		try:
			value = keyword['ascii']
		except:
			return


		changed = self.set (value)

		if changed == True:
			Event.queue (self.redraw)


	def setDefaultBackground (self, color):
		''' Set the default background color.
		'''

		if self['background'] == self.background:
			self['background'] = color

		if self.display['background'] == self.background:
			self.display['background'] = color

		self.background = color


	def setDefaultForeground (self, color):
		''' Set the default foreground color.
		'''

		if self.display['foreground'] == self.foreground:
			self.display['foreground'] = color

		self.foreground = color


	def setLabel (self, label):
		''' Set the cosmetic label used by this Value when
		    describing itself. This label is used, at a minimum,
		    by Value.write() when putting a temporary message
		    up on the menu bar.
		'''

		if self.label == label:
			return False

		self.label = label
		return True


	def setKeyword (self, keyword, callback=True):
		''' Set the Keyword object used by this Value to
		    write new values.

		    If callback is set to True, the ktl.Keyword object will
		    be instructed to invoke self.receiveCallback() for any
		    KTL broadcasts. Note that setting callback to True will
		    also result in queueing up monitoring for this Keyword
		    if it is not already monitored.
		'''

		if self.keyword == keyword:
			return False


		old_keyword = self.keyword
		self.keyword = keyword


		datatype = keyword['type']

		if datatype == 'KTL_INT':
			self.setValidator (validateInteger)

		elif datatype == 'KTL_FLOAT' or datatype == 'KTL_DOUBLE':
			self.setValidator (validateFloat)

		if self.box != None and self.box.keywords != None:
			self.box.keywords[self.label] = keyword


		if old_keyword != None and callback == True:

			# Shut down the old callback, if any.
			# This condition is very unlikely to be True
			# in the typical case; instead, the caller
			# should invoke setKeyword (callback=False)
			# when necessary for special cases.

			old_keyword.callback (self.receiveCallback, remove=True)


		if callback == True:
			self.setCallback (keyword)

		return True


	def setCallback (self, keyword):
		''' Set up this Value object to receive callbacks
		    from the specified ktl.Keyword object. setCallback()
		    will also establish monitoring of the ktl.Keyword
		    if necessary.
		'''

		keyword.callback (self.receiveCallback)

		if keyword['monitored'] == True:
			self.receiveCallback (keyword)
		else:
			Monitor.queue (keyword)


	def setValidator (self, validator):
		''' Set the validation function, if any, that will
		    be used to check any 'chosen' user input for
		    validity.

		    The validation function should accept a string
		    value as its sole argument.
		'''

		if callable (validator):
			# Good, you...
			pass
		else:
			raise TypeError, 'validator must be callable'

		changed = False

		if self.validator != validator:

			self.validator = validator
			changed = True

		return changed


	def setKeepChoice (self, keep):
		''' If set to True, the 'choice' will not be cleared
		    when the user depresses the 'go' button. It also
		    will not be cleared if self.value == self.choice.
		'''

		changed = False

		if self.keep_choice != keep:

			self.keep_choice = keep
			changed = True

		return changed


	def keywords (self):
		''' Return a tuple of keywords associated with this
		    Value.
		'''

		keywords = []

		if self.keyword != None:
			keywords.append (self.keyword)

		keywords = tuple (keywords)

		return (keywords)


	def get (self):
		''' Return the currently displayed string, which may be
		    self.value or self.choice.
		'''

		try:
			value = self.display.get ()
		except AttributeError:
			value = self.display['text']

		return value


	def set (self, value):

		changed = False

		if value != self.value:

			self.value = value
			changed = True

			if value == self.choice and self.keep_choice == False:
				self.setChoice (None)

		return changed


	def setOverride (self, value=None):
		''' Override the displayed value with the requested
		    value. This mechanism allows external intervention
		    for special-case displays for what is otherwise a
		    perfectly well-behaved Value construct.

		    Note that a user's choice will still take precedence,
		    display-wise (see Value.redraw()).

		    To clear the override, call this method with an
		    argument of None, or no arguments at all.
		'''

		changed = False

		if value != self.override:
			self.override = value
			changed = True

		return changed


	def setChoice (self, choice):

		changed = False

		if self.keep_choice == False:

			if choice == self.value:
				choice = None

			elif isinstance (self.keyword, ktl.Keyword):

				# Attempt to do intelligent comparisons
				# for integer and floating point types.
				# For example, 1.1 should be treated as
				# equivalent to 1.100. If for some reason
				# the numeric casts fail, take no additional
				# action.

				datatype = self.keyword['type']

				if datatype == 'KTL_INT':
					try:
						test_choice = int (choice)
						test_value  = int (self.value)
					except:
						test_choice = True
						test_value  = False

					if test_choice == test_value:
						choice = None

				elif datatype == 'KTL_FLOAT' or datatype == 'KTL_DOUBLE':
					try:
						test_choice = float (choice)
						test_value  = float (self.value)
					except:
						test_choice = True
						test_value  = False

					if test_choice == test_value:
						choice = None


		self.validateChoice (choice)

		if choice != self.choice:

			self.choice = choice
			changed = True

		return changed


	def validateChoice (self, choice):

		if self.validator == None or choice == None or choice == '':
			# No validator, or an empty choice.
			# In either case, the choice is valid.

			self.valid = True

		else:
			if isinstance (self.keyword, ktl.Keyword):
				range = self.keyword['range']

				# If available, use the ascii representation
				# of the range. The values displayed by the
				# GUI are always the ascii representation,
				# so using the ascii range is appropriate.

				try:
					range = range['ascii']
				except (KeyError, TypeError):
					pass
			else:
				range = None

			try:
				self.validator (choice, range)
				self.valid = True

			except ValueError:
				self.valid = False

				exception = sys.exc_info ()[1]

				Log.alert ("Invalid value: %s" % (str (exception)))


	def choose (self, choice):
		''' Accept a new value as a choice. This is invoked by
		    any mechanism that does not rely on the user typing
		    text into the entry box-- such as loading an instrument
		    setup, or using the increment/decrement arrows.

		    If choice == None, any user choice is cleared.
		'''

		changed = self.setChoice (choice)

		if changed == True:

			self.redraw ()


	def update (self):
		''' Invoked by the toplevel widgets, this is our
		    prompt to re-evaluate the sizes of any subwidgets.
		'''

		try:
			self.go_button.update ()
		except AttributeError:
			pass


	def redraw (self):
		''' Depending on self.choice and self.value, choose
		    the appropriate value to be displayed.
		'''

		# Choose which value to display. If the user made
		# a choice, that takes precedence over the "real"
		# value of the Keyword object.

		if self.choice != None:
			value = self.choice

		elif self.override != None:
			value = self.override

		elif self.value != None:
			value = self.value

		else:
			# This should not happen, but it's possible if
			# a Value object is not set up correctly.
			value = '--'


		# Ensure the displayed value is current.

		try:
			self.display.set (value)
		except AttributeError:
			Event.tkSet (self.display, 'text', value)


		# Ensure the colors are correct.

		if self.choice == None:

			background = self.background
			foreground = self.foreground

		else:
			# There is a choice, and it should be highlighted.

			foreground = 'black'

			if self.valid == True:
				background = Color.selection

			elif self.valid == False:
				background = Color.invalid

			else:
				# This should never happen.
				raise RuntimeError, 'Value.valid is not a boolean'

		Event.tkSet (self.display, 'background', background)
		Event.tkSet (self.display, 'foreground', foreground)


		try:
			self.checkGoButton ()
		except AttributeError:
			pass


	def write (self, *ignored):
		''' Write self.choice to the keyword.
		'''

		if self.choice != None	and \
		   self.online == True	and \
		   self.enabled == True	and \
		   self.valid == True:

			try:
				self.keyword.write (self.choice, wait=False)
			except:
				Log.alert ("Unable to write '%s' to %s" % (self.choice, self.keyword['name']))
				ktl.log (ktl.LOG_ERROR, "GUI: Error writing '%s' to %s:\n%s" % (self.choice, self.keyword['name'], traceback.format_exc ()))
				return

			if self.messages == True:
				if self.label == None:
					keyword = self.keyword['name']
					message = "Wrote '%s' to %s" % \
						(self.choice, keyword)
				else:
					message = "%s set to '%s'" % \
						(self.label, self.choice)

				Log.alert (message)

			# The 'write' action is more affirmative if the
			# user's choice clears immediately. This can be
			# overridden with setKeepChoice().

			if self.keep_choice == False:

				self.choose (None)


	def enableActivity (self):
		''' Enable direct (non-broadcast) keyword activity.
		'''

		if self.enabled == False or self.online == False:
			return

		try:
			self.display.enableActivity ()
		except AttributeError:
			Event.tkSet (self.display, 'state', Tkinter.NORMAL)

		try:
			self.checkGoButton ()
		except AttributeError:
			pass


	def disableActivity (self):
		''' Disable any direct (non-broadcast) keyword activity
		    until further notice.
		'''

		if self.enabled == True and self.online == True:
			# disableActivity() should not get invoked
			# without one of the above being true.

			Log.error ('disableActivity() invoked while fully enabled?')
			return

		try:
			self.loseFocus ()
		except AttributeError:
			pass

		try:
			self.display.disableActivity ()
		except AttributeError:
			Event.tkSet (self.display, 'state', Tkinter.DISABLED)

		try:
			self.checkGoButton ()
		except AttributeError:
			pass


	def enable (self):
		''' The reverse operation of disable().
		'''

		if self.enabled == True:
			return

		self.enabled = True

		self.enableActivity ()


	def disable (self):
		''' Render a Value object largely inert, until such time that
		    Value.enable() is called.
		'''

		if self.enabled == False:
			return

		self.enabled = False

		if self.choice != None:
			self.choose (None)

		if self.focused:
			self.loseFocus ()

		self.disableActivity ()


	def connect (self):
		''' Assert that the Value once again has connectivity
		    to its KTL service.
		'''

		if self.online == True:
			return

		self.online = True

		self.enableActivity ()


	def disconnect (self):
		''' This Value object should behave as if it has no
		    connection to its KTL service.
		'''

		if self.online == False:
			return

		self.online = False

		self.disableActivity ()


# end of class Value



class Label (Value):
	''' Dumb-down a Value object to be a Keyword-aware text label,
	    without any component images.
	'''

	def __init__ (self, master, box=None, main=None, top=None):

		Value.__init__ (self, master=master,
				  background = Color.white,
				  foreground = Color.value,
				  anchor = Tkinter.W,
				  justify = Tkinter.LEFT,
				  box = box,
				  go = False)

		# Wrap length for a Label display. Default is
		# 40 characters, and is adjusted via setWrap().

		self.wrap_length = 40

		# Initialize the wraplength parameter, which depends
		# on the font size.

		self.update ()


	def update (self):

		if self.wrap_length != None:
			# Wrap the displayed value if it's really long.
			# The 'wraplength' value is in pixels. Multiply
			# the font size by 40 to wrap at 40 characters.

			font_size = Font.display.cget ('size')

			size = font_size * self.wrap_length

			Event.tkSet (self.display, 'wraplength', size)


	def setWrap (self, wrap=40):
		''' Set the wrap length in characters for the Label.
		    A wrap length of None or 0 indicates that no wrapping
		    is desired.
		'''

		if wrap != None:
			# Must be an integer.

			try:
				wrap = int (wrap)
			except:
				raise TypeError, "sole argument to setWrap () must be None or an integer"

			if wrap == 0:
				wrap = None


		if wrap != self.wrap_length:
			self.wrap_length = wrap
			return True

		return False


	def setChoice (self, *ignored):
		return False


	def choose (self, *ignored):
		pass


	def setKeyword (self, keyword, callback=True):
		''' In addition to the default processing, set our
		    width if the keyword in question is an enumerated
		    type.
		'''

		changed = Value.setKeyword (self, keyword, callback)

		if changed == False:
			return False


		type = keyword['type']

		if type == 'KTL_ENUM' or type == 'KTL_BOOLEAN':

			length = 0
			for enumerator in keyword['enumerators']:

				length = max (length, len (enumerator))

			if length > 0:

				Event.tkSet (self.display, 'width', length)

		return True


# end of class Label



class ERRLabel (Label):
	''' A Label with extra interpretation of ERR keyword values.
	'''

	def receiveCallback (self, keyword):
		''' If the ERR value is 0, display descriptive text instead.
		'''

		if keyword['populated']:
			try:
				value = keyword['ascii']
			except:
				value = 'none'
		else:
			value = 'none'

		if value == '0':
			value = 'none'

		changed = self.set (value)

		if changed == True:
			Event.queue (self.redraw)


# end of class ERRLabel



class MSGLabel (Label):
	''' A Label with extra interpretation of MSG keyword values.
	'''

	def receiveCallback (self, keyword):
		''' If the MSG value is '', display descriptive text instead.
		'''

		if keyword['populated']:
			try:
				value = keyword['ascii']
			except:
				value = 'none'
		else:
			value = 'none'

		if value == '':
			value = 'none'

		changed = self.set (value)

		if changed == True:
			Event.queue (self.redraw)


# end of class MSGLabel



class XMVLabel (Label):
	''' A Label with extra interpretation of XMV keyword values.
	'''

	def receiveCallback (self, keyword):
		''' If the XMV value is '', display descriptive text instead.
		'''

		if keyword['populated']:
			try:
				value = keyword['ascii']
			except:
				value = 'unknown'
		else:
			value = 'unknown'

		if value == '':
			value = 'no'

		changed = self.set (value)

		if changed == True:
			Event.queue (self.redraw)


# end of class XMVLabel



class Stepper (Label):
	''' A Value object that has forward/reverse buttons as well as
	    an immutable display of the current value. When one of the
	    buttons is activated, an absolute value will be written to
	    the step-wise keyword assigned via setRelativeKeyword().

	    A non-relative keyword should be assigned via setKeyword()
	    for the main display.
	'''

	def __init__ (self, master, box=None, main=None, top=None):

		# Establish an empty tuple at self.buttons to allow
		# the parent __init__() to complete successfully.
		self.buttons = ()

		Label.__init__ (self, master, box=box, main=main, top=top)

		# Relative keyword used for writing the increment steps.

		self.relative = None

		# Default increments used for the buttons, changed via the
		# setIncrement() method.

		self.increment_small = 2
		self.increment_large = 10

		# Our frame will have five columns: the traditional Label
		# in the middle, flanked by a pair of buttons on either side.
		# Re-grid the label accordingly.

		Event.tkSet (self.display, 'width', 5)
		Event.tkSet (self.display, 'anchor', Tkinter.CENTER)

		self.display.grid (row=0, column=2, sticky=N+E+S, padx=2)


		# Establish the local button instances.

		self.forward_small = Button.Increment (self, main)
		self.forward_large = Button.Increment (self, main)
		self.reverse_small = Button.Increment (self, main)
		self.reverse_large = Button.Increment (self, main)

		self.buttons = (self.forward_small, self.forward_large, self.reverse_small, self.reverse_large)

		self.forward_small.setImage (Images.get ('forward_small'))
		self.forward_large.setImage (Images.get ('forward_large'))
		self.reverse_small.setImage (Images.get ('reverse_small'))
		self.reverse_large.setImage (Images.get ('reverse_large'))

		self.forward_small.redraw ()
		self.forward_large.redraw ()
		self.reverse_small.redraw ()
		self.reverse_large.redraw ()

		Event.tkSet (self.forward_small, 'compound', Tkinter.RIGHT)
		Event.tkSet (self.forward_large, 'compound', Tkinter.RIGHT)
		Event.tkSet (self.reverse_small, 'compound', Tkinter.LEFT)
		Event.tkSet (self.reverse_large, 'compound', Tkinter.LEFT)

		self.setIncrement (self.increment_small, self.increment_large)

		sticky = N + E + S + W

		self.reverse_large.grid (row=0, column=0, sticky=sticky)
		self.reverse_small.grid (row=0, column=1, sticky=sticky)
		self.forward_small.grid (row=0, column=3, sticky=sticky)
		self.forward_large.grid (row=0, column=4, sticky=sticky)


	def setIncrement (self, small=None, large=None):

		changed = False

		if small != None:
			small = abs (small)

		if large != None:
			large = abs (large)

		if self.increment_small != small and small != None:
			self.increment_small = small
			changed = True

			self.forward_small.setIncrement (small)
			self.reverse_small.setIncrement (-small)


		if self.increment_large != large and large != None:
			self.increment_large = large
			changed = True

			self.forward_large.setIncrement (large)
			self.reverse_large.setIncrement (-large)


		return changed


	def setRelativeKeyword (self, keyword):

		if self.relative == keyword:
			return False

		self.relative = keyword

		for button in self.buttons:
			button.setKeyword (keyword)

		return True


	def createHighlight (self):

		for button in self.buttons:
			button.createHighlight ()


	def removeHighlight (self):

		for button in self.buttons:
			button.removeHighlight ()


	def update (self):

		Label.update (self)

		for button in self.buttons:
			button.update ()


	def redraw (self):

		Label.redraw (self)

		Event.tkSet (self.forward_small, 'text', self.increment_small)
		Event.tkSet (self.reverse_small, 'text', self.increment_small)
		Event.tkSet (self.forward_large, 'text', self.increment_large)
		Event.tkSet (self.reverse_large, 'text', self.increment_large)


# end of class Stepper



class Jogger (Value):
	''' A Value object that has forward/reverse buttons as well as
	    an immutable display of the current value. When one of the
	    buttons is activated, an absolute value will be written to
	    the 'jogger' keyword assigned by setJogKeyword(). When
	    jogging, the value display will turn into a 'stop' button,
	    which will issue a keyword write as assigned by setStopKeyword()
	    and setStopValue().

	    A keyword reflecting the actual value should be assigned via
	    setKeyword() for the main display.
	'''

	def __init__ (self, master, box=None, main=None, top=None):

		# Our display element will be a button.

		display = TextButton

		arguments = {'master':	self,
			     'main':	box.main}

		Value.__init__ (self,
				master	= master,
				box	= box,
				go	= False,
				top	= top,
				anchor	= Tkinter.CENTER,
				justify	= Tkinter.CENTER,
				display	= display,
				arguments = arguments)

		# Jogging keyword used for this value object,
		# set by setJogKeyword(). This is typically
		# a speed keyword.

		self.jog_keyword = None

		# Jog mode keyword used for this value object,
		# set by setModeKeyword() and setJogMode().
		# This keyword will be used to determine whether
		# the stage is genuinely in motion.

		self.mode_keyword = None
		self.jog_value = 'jog'

		# Values used for stopping the stage, set by
		# setStopKeyword() and setStopValue().

		self.stop_keyword = None
		self.stop_value = None

		# Default values used for the buttons, set by setJogSpeed().

		self.jog_small = 50
		self.jog_large = 100

		self.currently_jogging = None
		self.hovering = False

		# Our frame will have five columns: the button in the middle,
		# flanked by a pair of buttons on either side.

		self.display.grid (row=0, column=2, sticky=N+E+S, padx=2)


		# Establish the local button instances.

		self.forward_small = JoggerButton (self, main)
		self.forward_large = JoggerButton (self, main)
		self.reverse_small = JoggerButton (self, main)
		self.reverse_large = JoggerButton (self, main)

		self.forward_small.setImage (Images.get ('forward_small'))
		self.forward_large.setImage (Images.get ('forward_large'))
		self.reverse_small.setImage (Images.get ('reverse_small'))
		self.reverse_large.setImage (Images.get ('reverse_large'))

		self.buttons = (self.forward_small, self.forward_large, self.reverse_small, self.reverse_large)

		self.setJogSpeed (self.jog_small, self.jog_large)

		sticky = N + E + S + W

		self.reverse_large.grid (row=0, column=0, sticky=sticky)
		self.reverse_small.grid (row=0, column=1, sticky=sticky)
		self.forward_small.grid (row=0, column=3, sticky=sticky)
		self.forward_large.grid (row=0, column=4, sticky=sticky)

		for button in self.buttons:
			button.redraw ()

			# Default rendering of the component buttons should
			# be flat. It will be modified by calls to
			# createHighlight() and removeHighlight().

			Event.tkSet (button, 'relief', Tkinter.FLAT)

		Event.tkSet (self.display, 'relief', Tkinter.FLAT)

		# Customize the TextButton in the center for our
		# needs.

		Event.tkSet (self.display, 'command', self.stopJogging)
		Event.tkSet (self.display, 'activebackground', Color.invalid)

		self.jogging (False)

		self.display.bind ('<Enter>', self.hoverOn)
		self.display.bind ('<Leave>', self.hoverOff)


	def setJogKeyword (self, keyword, callback=True):

		if self.jog_keyword == keyword:
			return False

		self.jog_keyword = keyword

		for button in self.buttons:
			button.setJogKeyword (keyword)

		if callback == True:
			keyword.callback (self.jogCallback)
			Monitor.queue (keyword)

		return True


	def setJogSpeed (self, small, large):

		self.jog_small = abs (small)
		self.jog_large = abs (large)

		self.forward_small.setJogSpeed (small)
		self.reverse_small.setJogSpeed (-small)
		self.forward_large.setJogSpeed (large)
		self.reverse_large.setJogSpeed (-large)


	def setModeKeyword (self, keyword, callback=True):

		if self.mode_keyword == keyword:
			return False

		self.mode_keyword = keyword

		for button in self.buttons:
			button.setModeKeyword (keyword)

		if callback == True:
			keyword.callback (self.jogCallback)
			Monitor.queue (keyword)

		return True


	def setJogValue (self, mode):

		if self.jog_value == mode:
			return False

		self.jog_value = mode.lower ()

		for button in self.buttons:
			button.setJogMode (mode)

		return True


	def setStopKeyword (self, keyword, callback=True):

		if self.stop_keyword == keyword:
			return False

		self.stop_keyword = keyword

		if callback == True:
			keyword.callback (self.jogCallback)
			Monitor.queue (keyword)

		return True


	def setStopValue (self, value):

		self.stop_value = value.lower ()
		return True


	def jogging (self, active=True):
		''' This method changes the central button to be
		    a 'stop' button if jogging is asserted to be
		    active.
		'''

		if self.currently_jogging == active:
			return

		self.currently_jogging = active


		if active == True:
			self.display.enableActivity ()
			self.background = Color.selection
		else:
			self.display.disableActivity ()
			self.background = 'white'

		self.checkHover ()


	def hoverOn (self, *ignored):

		self.hovering = True
		self.checkHover ()


	def hoverOff (self, *ignored):

		self.hovering = False
		self.checkHover ()


	def checkHover (self):

		if self.hovering == True and self.currently_jogging == True:
			override = 'Stop'
		else:
			override = None

		changed = self.setOverride (override)

		if changed == True:
			self.redraw ()


	def jogCallback (self, keyword):
		''' This callback will be registered with the keywords
		    provided to setJogKeyword, setModeKeyword() and
		    setStopKeyword(). self.jogging() will be invoked after
		    inspection of the values.
		'''

		try:
			value = keyword['ascii'].lower ()
		except:
			return

		jogging = False

		if keyword == self.mode_keyword and value == self.jog_value:

			jogging = True

		elif keyword == self.stop_keyword and value == self.stop_value:

			jogging = False

		elif keyword == self.jog_keyword:

			value = int (value)
			if value == 0:

				# Also fire off a request for an explicit stop.
				# Otherwise, the typical behavior is for the
				# mode to remain 'Jogging' with a speed of zero,
				# which means the yellow highlighting for the
				# displayed value also remains active.

				# This must be a queued event, because we are
				# in the middle of a KTL callback context.
				# Invoking another KTL function here will
				# result in deadlock.

				if self.currently_jogging == True:
					Event.queue (self.stop_keyword.write, self.stop_value, False)

			# The self.jog_keyword does not by itself indicate
			# whether or not we are jogging. Return now, and
			# make no further changes.

			return


		if self.currently_jogging != jogging:
			Event.queue (self.jogging, jogging)


	def stopJogging (self, *ignored):
		''' Write the stop value to the stop keyword. If the
		    callback is registered correctly, we will see the
		    change in state, and update the display after
		    receiving the keyword broadcast.
		'''

		if self.stop_keyword == None:
			raise RuntimeError, "Jogger stop keyword not set"

		if self.stop_value == None:
			raise RuntimeError, "Jogger stop value not set"

		try:
			self.stop_keyword.write (self.stop_value, wait=False)
		except:
			Log.alert ("Unable to write '%s' to %s" % (self.choice, self.keyword['name']))
			ktl.log (ktl.LOG_ERROR, "GUI: Error writing '%s' to %s:\n%s" % (self.choice, self.keyword['name'], traceback.format_exc ()))


	def createHighlight (self):

		for button in self.buttons:
			button.createHighlight ()

		self.display.createHighlight ()


	def removeHighlight (self):

		for button in self.buttons:
			button.removeHighlight ()

		self.display.removeHighlight ()


	def update (self):

		Value.update (self)

		for button in self.buttons:
			button.update ()

		self.display.update ()


	def enableActivity (self):

		Value.enableActivity (self)

		for button in self.buttons:
			button.enableActivity ()


	def disableActivity (self):

		Value.disableActivity (self)

		for button in self.buttons:
			button.disableActivity ()


# end of class Jogger



class ScrollingText (Value):
	''' A read-only text area with a scroll bar. Useful for log windows.
	'''

	def __init__ (self, master, box=None, main=None, top=None):

		self.autoscroll = True
		self.maxlines = 200

		display = Tkinter.Text
		arguments = {'master':		self,
			     'height':		8,
			     'state':		Tkinter.DISABLED,
			     'wrap':		Tkinter.WORD}

		Value.__init__ (self, master=master,
				  background=Color.white,
				  foreground=Color.value,
				  anchor=Tkinter.W,
				  justify=Tkinter.LEFT,
				  box=box,
				  go=False,
				  display=display,
				  arguments=arguments)

		self.scrollbar = Tkinter.Scrollbar (self)
		self.scrollbar.grid (row=0, column=1, sticky=N+E+S+W)

		self.display['yscrollcommand'] = self.scrollbar.set
		self.scrollbar['command'] = self.display.yview


	def lineCount (self):

		# The value returned by index() is a line.column text string.
		# For a text area with complete lines, the column is typically
		# zero, and the line value is for the next line _after_ the
		# end of the current text. So, you subtract one to get the
		# total number of lines displayed.

		line_count = self.display.index (Tkinter.END)
		line_count = line_count.split ('.')[0]
		line_count = int (line_count)

		return line_count


	def setChoice (self, *ignored):
		return False


	def choose (self, *ignored):
		pass


	def set (self, value):

		value = value + '\n'
		Event.queue (Event.tkSet, self.display, 'state', Tkinter.NORMAL)
		Event.queue (self.display.insert, Tkinter.END, value)
		Event.queue (Event.tkSet, self.display, 'state', Tkinter.DISABLED)

		if self.autoscroll == True:
			Event.queue (self.display.yview, Tkinter.END)

		return True


	def setMaxLines (self, maximum):

		maximum = int (maximum)

		previous = self.maxlines
		self.maxlines = maximum

		if previous < maximum:
			self.update ()


	def setAutoScroll (self, autoscroll):

		if autoscroll == False:
			autoscroll = False
		else:
			autoscroll = True

		self.autoscroll = autoscroll


	def truncate (self, maximum):
		''' Truncate the displayed text to the 'maximum' quantity
		    of lines.
		'''

		spillover = self.lineCount () - maximum

		if spillover > 0:

			delete_begin = '1.0'
			delete_end = "%d.0" % (spillover + 1)

			self.display.delete (delete_begin, delete_end)


	def update (self):

		Event.queue (Event.tkSet, self.display, 'state', Tkinter.NORMAL)
		Event.queue (self.truncate, self.maxlines)
		Event.queue (Event.tkSet, self.display, 'state', Tkinter.DISABLED)

	redraw = update


# end of class ScrollingText



class SettableEntry (Tkinter.Entry):
	''' A Tkinter.Entry box with set() and get() methods,
	    for use as a Value.display object.
	'''

	def __init__ (self, master, textvariable):

		Tkinter.Entry.__init__ (self, master,
					font=Font.input,
					background=Color.white,
					foreground=Color.value,
					justify=Tkinter.RIGHT,
					textvariable=textvariable,
					width=7,
					borderwidth=0,
					highlightthickness=1,
					highlightbackground=Color.highlight)

		self.input = textvariable


	def set (self, value):

		self.input.set (value)

		# Always assert that this invocation of set() changed
		# the known value.

		return True


	def get (self):

		return (self.input.get ())


# end of class SettableEntry



class Entry (Value):
	''' A small frame that contains an input box, arrows to increment
	    or decrement the value, as well as a "go" button if the displayed
	    value is changed by the user.
	'''

	def __init__ (self, master, box=None, go=True, arrows=True, main=None, top=None):

		# Direct, per-keystroke access to user input.

		self.input = Tkinter.StringVar ()

		# Our display element will be an entry box.

		display = SettableEntry

		arguments = {'master':		self,
			     'textvariable':	self.input}

		Value.__init__ (self, master, box=box, main=main, top=top,
				go=go, display=display, arguments=arguments,
				borderwidth=1)

		# Is the cursor active in this widget?

		self.focused = False

		# Timer event to lose focus.

		self.expire_focus = None

		# How much the up+down arrows will change the value by.
		# This gets changed by self.setIncrement().

		self.increment_by = 10

		# Populate self.up_image[tk] and self.down_image[tk].

		self.arrows = arrows

		if arrows == True:

			self.up_button = Button.Simple (self, self.main, fontsized=True)
			self.up_button['borderwidth'] = 0
			self.up_button['command'] = self.increment
			self.up_button.setScale (0.5)
			self.up_button.setImage (Images.get ('up'))
			self.up_button.redraw ()

			self.down_button = Button.Simple (self, self.main, fontsized=True)
			self.down_button['borderwidth'] = 0
			self.down_button['command'] = self.decrement
			self.down_button.setScale (0.5)
			self.down_button.setImage (Images.get ('down'))
			self.down_button.redraw ()

			self.up_button.grid   (row=0, column=0, sticky=N+W+S)
			self.down_button.grid (row=1, column=0, sticky=N+W+S)


		self.display.grid (row=0, column=1, rowspan=2, sticky=N+E+S+W)

		if go == True:
			self.go_button.grid (row=0, column=2, rowspan=2, sticky=W)

		# Pay attention to whether someone might be entering text.

		self.display.bind ('<FocusIn>', self.focusIn)
		self.display.bind ('<FocusOut>', self.focusOut)

		self.display.bind ('<KeyPress-Return>', self.loseFocus)
		self.display.bind ('<KeyPress-Escape>', self.clearChoice)

		# Grab all text entry right away. Use trace here instead
		# of binding to Any-KeyPress, as doing the latter triggers
		# after the key is pressed, but *before* the value is added
		# to the Tkinter.Entry.get() value. By watching the StringVar
		# associated with the Entry box, we avoid that timing issue.

		self.input.trace ('w', self.gotInput)


	def clearChoice (self, *ignored):
		''' Wrapper to Entry.choose (None), discarding
		    any unnecessary event information.
		'''

		self.loseFocus ()
		self.choose (None)


	def choose (self, choice):
		''' If the value chosen is None, make sure we lose focus.
		'''

		Value.choose (self, choice)

		# We cannot check self.focused here, because if someone
		# clicks into top-level menu to, say, clear all choices,
		# a focusOut event will be triggered, and self.focused
		# will become False. Once the menu operation is triggered,
		# or cancelled, focus immediately returns to the window.

		# Thus, we are somewhat arbitrary about losing focus here,
		# and may be attempting to lose focus altogether too often.

		if choice == None:
			self.loseFocus ()


	def setIncrement (self, amount):
		''' Set the magnitude of the increment/decrement operation.
		'''

		amount = abs (amount)
		changed = False

		if self.increment_by != amount:

			self.increment_by = amount
			changed = True

		return changed


	def increment (self, amount=None):
		''' Increment the chosen value by the specified amount.
		'''

		if amount == None:
			amount = self.increment_by

		if self.choice != None:
			new_value = self.choice
		elif self.value != None:
			new_value = self.value
		else:
			new_value = 0

		if type (new_value) == int or type (new_value) == float:
			pass
		else:
			# Cast the value to an integer, or if that doesn't
			# work, a floating point number.

			try:
				new_value = int (new_value)
			except ValueError:
				try:
					new_value = float (new_value)
				except:
					# Some type of bad, non-numeric
					# input is present in the box.
					# The empty string is one common
					# example.

					new_value = 0

		# Turn it back into a string once we're done.

		new_value = str (new_value + amount)

		self.choose (new_value)


	def decrement (self, amount=None):
		''' Decrement the chosen value by the specified amount.
		'''

		if amount == None:
			amount = self.increment_by
		else:
			amount = abs (amount)

		self.increment (-amount)


	def gotInput (self, *ignored):
		''' Store any and all user input for immediate reference.
		'''

		if self.focused:
			new_choice = self.input.get ()

			if new_choice != self.choice:
				self.choose (new_choice)

			# Update focus expiration.

			self.expireFocus ()


	def focusIn (self, *ignored):
		self.focused = True
		self.expireFocus ()

		if self.keep_choice == True and self.choice == None:
			self.choose (self.value)


	def focusOut (self, *ignored):
		self.focused = False

		# If the entered value is the empty string, clear
		# the choice.

		if self.choice == '':
			self.choose (None)


	def loseFocus (self, *ignored):

		# Eliminate any pending events that would re-invoke
		# loseFocus() after focus has already been lost.

		if self.expire_focus != None:
			self.after_cancel (self.expire_focus)
			self.expire_focus = None

		# If we have the focus, lose it.

		if self.focused == True:

			# Pre-emptively set self.focused to False here,
			# because future or pending functions may inspect
			# self.focused before it is set by self.focusOut().

			self.focused = False
			self.top.focus ()


	def expireFocus (self):

		if self.focused:
			# Eliminate any pending events from previous
			# invocations of expireFocus().

			if self.expire_focus != None:
				self.after_cancel (self.expire_focus)

			# After 30 seconds, drop focus.

			self.expire_focus = self.after (30000, self.loseFocus)


	def enableActivity (self):

		Value.enableActivity (self)

		if self.arrows == True:

			self.up_button.enableActivity ()
			self.down_button.enableActivity ()


	def disableActivity (self):

		Value.disableActivity (self)

		if self.arrows == True:

			self.up_button.disableActivity ()
			self.down_button.disableActivity ()


	def update (self):

		Value.update (self)

		if self.arrows == True:

			self.up_button.update ()
			self.down_button.update ()


# end of class Entry



class TextEntry (Entry):
	''' Same as :class:`Entry`, but wider by default, and without
	    increment/decrement functionality.
	'''

	def __init__ (self, *arguments, **keyword_arguments):

		keyword_arguments['arrows'] = False

		Entry.__init__ (self, *arguments, **keyword_arguments)

		Event.tkSet (self.display, 'width', 15)
		Event.tkSet (self.display, 'justify', Tkinter.LEFT)


# end of class TextEntry



class SettableMenubutton (Tkinter.Menubutton):
	''' A Tkinter.Menubutton with set() and get() methods,
	    for use as a Value.display object.
	'''

	def __init__ (self, master):

		Tkinter.Menubutton.__init__ (self, master,
						text = '--',
						background = Color.white,
						foreground = Color.value,
						activebackground = Color.highlight,
						activeforeground = 'black',
						font = Font.display,
						justify = Tkinter.RIGHT,
						anchor = Tkinter.E,
						relief = Tkinter.FLAT,
						cursor = 'hand2',
						highlightthickness = 1,
						padx = 1,
						pady = 1)


	def set (self, value):

		return Event.tkSet (self, 'text', value)


	def get (self):

		# Don't catch TclError exceptions here, since this is a
		# problem the caller really wants to be aware of.

		return self['text']


	def enableActivity (self):

		Event.tkSet (self, 'cursor', 'hand2')
		Event.tkSet (self, 'state', Tkinter.NORMAL)


	def disableActivity (self):

		Event.tkSet (self, 'cursor', '')
		Event.tkSet (self, 'state', Tkinter.DISABLED)


# end of class SettableMenubutton



class MenuWithEntry (Entry):
	''' A Entry object that, for the most part, displays choices
	    as a menu until the user selects the 'Other...' menu option,
	    at which point it looks like an entry box.

	    Positions in the menu are defined arbitrarily, as opposed to
	    dynamically via a RON or PEN keyword.
	'''

	def __init__ (self, master, box=None, main=None, top=None, go=True, arrows=True):

		Entry.__init__ (self, master, box=box, main=main, top=top, go=go, arrows=arrows)

		self.values = ()
		self.alternates = ()
		self.names = ()
		self.excluded = {'home': True,
				 'irregular': True,
				 'unknown': True}

		self.menu_keyword = None
		self.main_keyword = None

		self.menu_validator = None
		self.main_validator = None

		# The Entry object gave us an entry box. We need to
		# keep a unique reference to it, so that it can be
		# swapped in and out with the menu.

		self.entry_box = self.display

		# Create our local menu.

		self.other = True
		self.menu_changed = False
		self.menu_items = ()

		self.menu_button = SettableMenubutton (self)

		self.menu = Tkinter.Menu (self.menu_button,
						foreground = 'black',
						tearoff = False,
						background = Color.menu,
						activebackground = Color.highlight,
						activeforeground = 'black',
						font = Font.display,
						relief = Tkinter.SOLID)

		self.menu_button['menu'] = self.menu

		# Display the menu by default.

		self.display = self.menu_button

		self.entry_box.grid_remove ()

		if self.arrows == True:
			self.up_button.grid_remove ()
			self.down_button.grid_remove ()

		self.menu_button.grid (row=0, column=0, rowspan=2, columnspan=2, sticky=N+E+S)

		if box != None:
			# Maintain highlight if someone is in the menu.

			self.menu.bind ('<Enter>', box.createHighlight)


	def setKeyword (self, keyword, callback=True):

		changed = Value.setKeyword (self, keyword, callback)

		if changed == True:
			self.main_keyword = keyword

			if self.validator != None:
				self.main_validator = self.validator

		return changed


	def setMenuKeyword (self, keyword, callback=True):

		if self.menu_keyword == keyword:
			return False

		self.menu_keyword = keyword

		datatype = keyword['type']

		if datatype == 'KTL_INT':
			self.menu_validator = validateInteger

		elif datatype == 'KTL_FLOAT' or datatype == 'KTL_DOUBLE':
			self.menu_validator = validateFloat

		if callback == True:
			self.setCallback (keyword)

		return True


	setAuxKeyword = setMenuKeyword


	def setMenu (self, menu_items):

		menu_items = tuple (menu_items)

		if menu_items == self.menu_items:
			return False

		self.menu_items = menu_items
		self.menu_changed = True

		return True


	def receiveCallback (self, keyword):
		''' Accepts a ktl.Keyword object, and sets the displayed
		    value correctly depending on the keyword and keyword
		    value.

		    This is expected to be used in conjunction
		    with Keyword.callback() and Keyword.monitor().
		'''

		if keyword['populated']:
			try:
				value = keyword['ascii']
			except:
				value = None
		else:
			value = None

		apply = False
		changed = False


		suffix = keyword['name'][-3:].upper ()
		setFunction = None

		if suffix == 'RON':
			setFunction = self.setRONMenu
		elif suffix == 'PEN':
			setFunction = self.setPENMenu
		elif suffix == 'NMS':
			setFunction = self.setNMSMenu
		elif suffix == 'NPX':

			if self.menu_type == 'RON':
				setFunction = self.setRONMenu
			elif self.menu_type == 'PEN':
				setFunction = self.setPENMenu
			elif self.menu_type == 'NMS':
				setFunction = self.setNMSMenu

			# Re-process the current menu value with the
			# new name prefix.

			service = self.main.services[keyword['service']]
			prefix  = keyword['name'][:-3]
			keyword = '%s%s' % (prefix, self.menu_type)

			keyword = service[keyword]

			if keyword['populated']:
				value = keyword['ascii']
			else:
				return

		if setFunction != None:
			changed = setFunction (value)


		if keyword == self.menu_keyword:
			if value in self.names:
				apply = True
			else:
				# Clear the display of the 'menu' value.
				# By setting self.value to None, we ensure
				# that the subsequent invocation of
				# self.receiveCallback() will follow the
				# self.value != menu_value branch below.

				self.value = None
				self.receiveCallback (self.main_keyword)

		elif keyword == self.main_keyword:
			# Let the menu keyword (typically, 'named' positions)
			# take precedence over the arbitrary values. This
			# allows Waveplate NAM == 'Out' to be displayed instead
			# of the VAL == '0.0000', which is generally broadcast
			# well after the NAM is updated.

			if self.menu_keyword == None:
				menu_value = None

			elif self.menu_keyword['populated']:
				try:
					menu_value = self.menu_keyword['ascii']
				except:
					menu_value = None
			else:
				menu_value = None

			if self.value != menu_value:
				apply = True


		if apply == True:
			# apply is only set to True if the keyword was
			# not part of the RON/PEN/NMS/NPX set. By construction,
			# this implies that 'changed' can only be False if
			# apply is True.

			changed = self.set (value)

		if changed == True:
			Event.queue (self.redraw)


	def buildMenu (self, values, names, alternates=None, other=True):
		''' Construct a menu based on the supplied list of positions
		    and names. The two lists will be stored internally,
		    and used to determine where to direct writes-- any writes
		    whose value matches a 'name' will go to self.menu_keyword,
		    and all other values will be written to self.keyword.

		    If alternates is specified, it will be used as an
		    alternate list of menu values, and an option will be
		    added to the menu to allow switching between self.values
		    and self.alternates.

		    An 'Other...' option will be added to the end of the menu
		    if the 'other' argument is True (the default).
		'''

		self.other = other
		self.values = values
		self.names  = names
		self.alternates = alternates

		menu_items = []

		choices = []
		choices.extend (names)
		choices.extend (values)

		for choice in choices:
			command = self.makeChoice (choice)
			menu_items.append ((choice, command))

		# If specified, provide an option to swap to the other set of
		# values.

		if self.alternates != None and len (self.alternates) > 0:

			if len (self.alternates) > len (self.values):
				label = 'More options'
			elif len (self.alternates) < len (self.values):
				label = 'Fewer options'
			else:
				label = 'Other options'

			menu_items.append ((label, self.swapMenu))

		# If requested, tack on the 'other' option, enabling the
		# entry box.

		if other == True:
			menu_items.append (('Other...', self.raiseEntryBox))


		# Enact the changes to the menu.

		return self.setMenu (menu_items)


	def cancel (self, add=None, remove=None):
		''' Add or remove 'cancel' option on the end of the menu.
		    It is safe to invoke this method repeatedly; the cancel
		    option will only be added or removed exactly once.
		'''

		if add != True:
			add = False

		if remove != True:
			remove = False

		if add and remove:
			raise ValueError, 'cannot both add and remove a cancel menu option'

		last_index = self.menu.index (Tkinter.END)

		if last_index != None:
			label = self.menu.entrycget (last_index, 'label')

			if label == 'Cancel':
				if remove == True:
					# Remove separator and cancel option.
					self.menu.delete (last_index - 1, last_index)

			elif add == True:
				# Add separator and cancel option.
				self.menu.add_separator ()
				self.menu.add_command (label = 'Cancel',
					command = self.makeChoice (None))


	def makeChoice (self, value):
		''' Function generator to use self.choose in menu commands.
		'''

		function = lambda : self.choose (value)

		return function


	def swapMenu (self):
		''' Build a new menu based swapping self.alternates
		    and self.values.
		'''

		alternates = self.values
		values = self.alternates

		changed = self.buildMenu (values, self.names, alternates, self.other)

		if changed == True:
			self.redraw ()


	def raiseEntryBox (self, *ignored):
		''' Give the user an entry box with which to make an
		    arbitrary choice.
		'''

		self.display = self.entry_box

		self.menu_button.grid_remove ()

		if self.arrows == True:
			self.up_button.grid ()
			self.down_button.grid ()

		self.entry_box.grid ()

		self.display.focus_set ()

		# Seed the entry box with the 'active' value.

		# The extra condition here allows the entry box to
		# actually be displayed; if we only called self.choose(),
		# the instant self.choose (None) went through, the menu
		# would get re-raised due to the code in self.choose()
		# which allows the menu to be raised when a choice
		# is externally cleared.

		if self.choice != None:
			self.choose (self.choice)
		else:
			self.redraw ()


	def raiseMenu (self, *ignored):
		''' Bring back the menu, and put the 'Other...' entry box
		    back into the background.
		'''

		self.loseFocus ()

		self.display = self.menu_button

		self.entry_box.grid_remove ()

		if self.arrows == True:
			self.up_button.grid_remove ()
			self.down_button.grid_remove ()

		self.menu_button.grid ()

		# Make sure that the display is current.

		self.choose (self.choice)


	def focusOut (self, *ignored):
		''' In addition to the standard Entry method,
		    raise the menu if the entry box has no value.
		'''

		Entry.focusOut (self)

		current = self.input.get ()

		current = current.strip ()

		if current == '':
			self.choose (None)

		if self.choice == None or self.choice == self.value:
			self.raiseMenu ()


	def keywords (self):
		''' Return a tuple of keywords associated with this
		    Value.
		'''

		keywords = []

		if hasattr (self, 'main_keyword') and self.main_keyword != None:
			keywords.append (self.main_keyword)

		if hasattr (self, 'menu_keyword') and self.menu_keyword != None:
			keywords.append (self.menu_keyword)

		keywords = tuple (keywords)

		return (keywords)


	def write (self, *ignored):
		''' Set self.keyword to the appropriate Keyword object
		    for this particular value, and then invoke
		    Value.write().
		'''

		Value.write (self)

		# If necessary, bring back the menu.

		if self.display == self.entry_box:
			self.raiseMenu ()


	def choose (self, choice):
		''' If a choice is made, make sure there is a
		    'Cancel' option present in the menu, if
		    the menu is displayed. Also make sure that
		    the validation function is appropriate for
		    the chosen value.
		'''

		if hasattr (self, 'names'):
			if choice in self.names:
				if self.validator != self.menu_validator:
					self.validator = self.menu_validator

			elif self.validator != self.main_validator:
				self.validator = self.main_validator

		Entry.choose (self, choice)

		if self.display == self.menu_button:

			if self.choice == None:
				self.cancel (remove=True)
			else:
				self.cancel (add=True)

		elif choice == None:
			# The only way to choose None while the entry
			# box is displayed is for it to be an external
			# choice. When that occurs, the act of raising
			# the menu is not triggered by any other means.

			self.raiseMenu ()


	def redraw (self):
		''' Make sure that the Keyword object at self.keyword
		    is appropriate for the displayed value.
		'''

		Value.redraw (self)

		displayed = self.display.get ()

		changed = False

		if displayed in self.names:
			if self.keyword != self.menu_keyword:
				self.keyword = self.menu_keyword

				changed = True

		elif self.keyword != self.main_keyword:
			self.keyword = self.main_keyword

			changed = True


		if changed == True:
			if self.box != None and self.box.keywords != None:
				self.box.keywords[self.label] = self.keyword


		self.redrawMenu ()


	def redrawMenu (self):

		if self.menu_changed == False:
			return

		# Delete the old menu entries.

		last_index = self.menu.index (Tkinter.END)

		if last_index != None:
			self.menu.delete (0, last_index)

		menu_width = 0
		for menu_item in self.menu_items:

			if len (menu_item) == 0:
				self.menu.add_separator ()
				continue

			label	= menu_item[0]
			command = menu_item[1]

			menu_width = max (menu_width, len (label))
			self.menu.add_command (label=label, command=command)

		if menu_width > 0:
			Event.tkSet (self.menu_button, 'width', menu_width)

		self.menu_changed = False


	def setCallback (self, keyword):

		# Check the suffix to determine the type of menu
		# keyword being used.

		suffix = keyword['name'][-3:].upper ()

		if suffix == 'NMS' or suffix == 'PEN' or suffix == 'RON':
			self.menu_type = suffix

		Entry.setCallback (self, keyword)


	def setNMSMenu (self, value):
		''' Update the menu to correspond to the supplied mapping.
		'''

		names = Stage.parseNMS (value)

		# Get the name prefix, if any.

		if hasattr (self, 'menu_keyword') and self.menu_keyword != None:
			prefix = self.menu_keyword['name'][:-3] + 'NPX'
			service = self.menu_keyword['service']
		elif self.keyword != None:
			prefix = self.keyword['name'][:-3] + 'NPX'
			service = self.keyword['service']
		else:
			prefix = ''
			service = None

		if service != None and \
		   hasattr (self.main, 'services') and \
		   service in self.main.services   and \
		   prefix in self.main.services[service]:

			service = self.main.services[service]
			prefix	= service[prefix]

			if prefix['populated'] == True:
				prefix = prefix['ascii']
			else:
				prefix = ''
		else:
			prefix = ''


		menu_items = []
		choices = []

		for name in names:

			if name.lower () in self.excluded:
				continue

			# If the prefix is set, only include names that
			# match the prefix. If the prefix is not set,
			# always include the name.

			if prefix == '':
				pass
			else:
				if name.find (prefix) == 0:
					# Strip off the prefix for display.
					name = name[len (prefix):]
				else:
					# Prefix did not match. Skip.
					continue

			command = self.makeChoice (name)

			menu_items.append ((name, command))
			choices.append (name)


		# Is the current choice present in the new menu?

		if self.choice != None:
			if self.choice in choices:
				pass
			else:
				# Chosen name is no longer valid.
				self.choose (None)


		# Update the menu according to the new NMS value.

		if hasattr (self, 'names'):
			self.names = choices

		return self.setMenu (menu_items)


	def setPENMenu (self, value):
		''' Update the menu to correspond to the supplied mapping.
		'''

		pairs = Stage.parsePEN (value)

		menu_items = []
		names = []
		choices = []

		position = None
		name	 = None

		for pair in pairs:

			position = pair[0]
			name	 = pair[1]

			names.append (name)


		for name in names:

			if name.lower () in self.excluded:
				continue

			command = self.makeChoice (name)

			menu_items.append ((name, command))
			choices.append (name)


		# Is the current choice present in the new menu?

		if self.choice != None:
			if self.choice in names.values ():
				pass
			else:
				# Chosen name is no longer valid.
				self.choose (None)


		# Update the menu according to the new PEN value.

		if hasattr (self, 'names'):
			self.names = choices

		return self.setMenu (menu_items)


	def setRONMenu (self, value):
		''' Update the menu to correspond to the supplied mapping.
		'''

		triplets = Stage.parseRON (value)

		# Get the name prefix, if any.

		if hasattr (self, 'menu_keyword') and self.menu_keyword != None:
			prefix = self.menu_keyword['name'][:-3] + 'NPX'
			service = self.menu_keyword['service']
		elif self.keyword != None:
			prefix = self.keyword['name'][:-3] + 'NPX'
			service = self.keyword['service']
		else:
			prefix = ''
			service = None

		if service != None and \
		   hasattr (self.main, 'services') and \
		   service in self.main.services   and \
		   prefix in self.main.services[service]:

			service = self.main.services[service]
			prefix	= service[prefix]

			if prefix['populated']:
				prefix = prefix['ascii']
			else:
				prefix = ''
		else:
			prefix = ''


		menu_items = []

		names = {}
		choices = []

		for triplet in triplets:

			raw	= triplet[0]
			ordinal = triplet[1]
			name	= triplet[2]

			# If the prefix is set, only include names that
			# match the prefix. If the prefix is not set,
			# always include the name.

			if prefix == '':
				names[ordinal] = name
			else:
				if name.find (prefix) == 0:
					# Strip off the prefix for display.
					name = name[len (prefix):]
					names[ordinal] = name

		ordinals = names.keys ()
		ordinals.sort (sortStringAsNumber)

		for ordinal in ordinals:

			# Only display positions corresponding to ordinal
			# values larger than zero (typically the Home position).

			if int (ordinal) > 0:
				name = names[ordinal]
				command = self.makeChoice (name)

				menu_items.append ((name, command))
				choices.append (name)


		# Is the current choice present in the new menu?

		if self.choice != None:
			if self.choice in names.values ():
				pass
			else:
				# Chosen name is no longer valid.
				self.choose (None)


		# Update the menu according to the new RON value.

		if hasattr (self, 'names'):
			self.names = choices

		return self.setMenu (menu_items)


# end of class MenuWithEntry



class TemperatureEntry (MenuWithEntry):

	def __init__ (self, *arguments, **keyword_arguments):

		# Separate keywords are typically used to report the
		# setpoint and current temperature from a temperature
		# controller.

		self.temperature = None
		self.temperature_value = None

		MenuWithEntry.__init__ (self, *arguments, **keyword_arguments)

		self.setIncrement (5)

		self.buildMenu (('0', '50'), ())


	def keywords (self):

		keywords = []

		if self.keyword != None:
			keywords.append (self.keyword)

		if self.temperature != None:
			keywords.append (self.temperature)

		keywords = tuple (keywords)

		return keywords


	def setTemperatureKeyword (self, keyword, callback=True):

		if self.temperature == keyword:
			return False

		self.temperature = keyword

		if callback == True:
			self.setCallback (keyword)


	def receiveCallback (self, keyword):

		if keyword['populated'] == False:
			return

		try:
			value = keyword['ascii']
		except:
			return


		if keyword == self.keyword:
			# This is the setpoint. Save the value
			# as the "primary" value, so it gets
			# picked up by saved setups.

			self.set (value)

		else:
			# This is the temperature. Stash the value,
			# and conditionally invoke a redraw.

			if self.temperature_value != value:
				self.temperature_value = value

				Event.queue (self.redraw)


	def redraw (self):
		''' Display the temperature value, not the
		    setpoint value.
		'''

		setpoint_value = self.value
		self.value = self.temperature_value

		result = MenuWithEntry.redraw (self)

		self.value = setpoint_value
		return result


# end of class TemperatureEntry



class Menu (MenuWithEntry):

	''' Strip out the 'WithEntry' aspect of the parent class,
	    and bolt on the necessary smarts to render the menu
	    according to RON or PEN keywords.
	'''

	def __init__ (self, master, box=None, main=None, top=None, go=True):

		# What kind of menu keyword is in use here?

		self.menu_type = None

		# Invoke the base class without the increment/decrement arrows.

		MenuWithEntry.__init__ (self, master, box=box, main=main, top=top, go=go, arrows=False)

		# The MenuWithEntry object gave us an entry box.
		# We don't need it.

		del (self.input)
		del (self.entry_box)
		del (self.focused)
		del (self.expire_focus)

		# We also don't need the extra dual-keyword machinery.

		del (self.menu_keyword)
		del (self.names)
		del (self.values)
		del (self.alternates)


	def write (self, *ignored):
		''' Revert to Value.write() instead of MenuWithEntry's
		    version.
		'''

		return Value.write (self)


	def redraw (self):
		''' Revert to Value.redraw() instead of
		    MenuWithEntry's version, skipping
		    any manipulation of main_ and menu_ values.
		    However, we need to retain the notion of
		    redrawing the menu.
		'''

		Value.redraw (self)

		self.redrawMenu ()


	def keywords (self):
		''' Revert to Value.keywords() instead of MenuWithEntry's
		    version.
		'''

		return Value.keywords (self)


	def loseFocus (self, *ignored):
		''' No entry box here, don't manipulate the focus.
		'''

		pass


	def expireFocus (self):
		''' No entry box here, don't manipulate the focus.
		'''

		pass


	def receiveCallback (self, keyword):
		''' Accepts a ktl.Keyword object, and queues an
		    update to either the menu or the displayed
		    label, depending on the keyword.

		    This is expected to be used in conjunction
		    with Keyword.callback() and Keyword.monitor().
		'''

		if keyword['populated'] == False:
			return

		try:
			value = keyword['ascii']
		except:
			return


		suffix = keyword['name'][-3:].upper ()

		if suffix == 'NAM':
			setFunction = self.set
		elif suffix == 'RON':
			setFunction = self.setRONMenu
		elif suffix == 'PEN':
			setFunction = self.setPENMenu
		elif suffix == 'NMS':
			setFunction = self.setNMSMenu
		elif suffix == 'NPX':

			if self.menu_type == None:
				setFunction = None
			elif self.menu_type == 'RON':
				setFunction = self.setRONMenu
			elif self.menu_type == 'PEN':
				setFunction = self.setPENMenu
			elif self.menu_type == 'NMS':
				setFunction = self.setNMSMenu

			# Re-process the current menu value with the
			# new name prefix.

			if setFunction != None:
				service = self.main.services[keyword['service']]
				prefix  = keyword['name'][:-3]
				keyword = prefix + self.menu_type
				keyword = service[keyword]

				if keyword['populated']:
					value = keyword['ascii']
				else:
					return
		else:
			raise ValueError, "unhandled keyword suffix in Menu: %s" % (suffix)

		if setFunction == None:
			changed = False
		else:
			changed = setFunction (value)

		if changed == True:
			self.menu_changed = True
			Event.queue (self.redraw)


# end of class Menu



class ArbitraryMenu (Menu):
	''' A Menu object that has a set menu of choices, rather than
	    a menu provided dynamically via a RON or PEN keyword. This
	    object will populate the menu automatically if the keyword
	    passed to setKeyword() is an enumerated type.
	'''

	def receiveCallback (self, keyword):
		''' Revert to the simpler processing in the Value object. '''

		return Value.receiveCallback (self, keyword)


	def buildMenu (self, values):
		''' Construct a menu based on the supplied list of values.
		'''

		self.values = values

		menu_items = []

		for choice in self.values:

			if choice == '':
				continue

			if choice.lower () in self.excluded:
				continue

			command = self.makeChoice (choice)
			menu_items.append ((choice, command))


		# Determine what the display width should be, based on
		# the longest menu option.

		length = 0
		for pair in menu_items:

			enumerator = pair[0]
			length = max (length, len (enumerator))

		if length > 0:

			Event.tkSet (self.display, 'width', length)


		# Enact the changes to the menu.

		return self.setMenu (menu_items)


	def exclude (self, value, revoke=False):
		''' Exclude a specific option from the drop-down menu.
		    If the keyword is externally set to this value, it
		    will still be displayed as the current value, it
		    just isn't selectable via the menu. If *revoke* is
		    set to True, the exclusion for that value will be
		    removed. Exclusions are case-insensitive.
		'''

		value = value.lower ()

		if revoke == False:
			self.excluded[value] = True
		else:
			try:
				del self.excluded[value]
			except KeyError:
				pass

		if self.keyword != None:
			Event.queue (self.buildMenu, self.keyword['enumerators'])


	def setKeyword (self, keyword, callback=True):

		changed = Value.setKeyword (self, keyword, callback)

		if changed == False:
			return False

		type = keyword['type']

		if type == 'KTL_ENUM' or type == 'KTL_BOOLEAN':

			self.buildMenu (keyword['enumerators'])


		return True


# end of class ArbitraryMenu
