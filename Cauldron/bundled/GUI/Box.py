import version
version.append ('$Revision: 88896 $')
del version


import Tkinter
from Tkinter import N, E, S, W

import Button
import Color as kColor		# avoid name conflict with class Color below
import Value


class Color (Tkinter.Frame):

	def __init__ (self, main, column=None, background='#000000'):

		Tkinter.Frame.__init__ (self, main.frame, background=background)

		self.main = main

		if column == None:
			column = len (main.color_boxes) * 3


		main.color_boxes.append (self)

		self.label_column  = column
		self.value_column  = column + 1
		self.button_column = column + 2

		# Make sure that we fill our assigned space.

		self.grid (row=0, column=column, columnspan=3, sticky=N+E+S+W)

		main.frame.columnconfigure (column, weight=1)

		# Each box retains a notion of what the next available
		# row will be.

		self.next_row = 0
		self.max_span = 1

		# Keep a list of the Info objects in each Color box.

		self.boxes = []


	def rowTick (self, quantity=1):
		''' Return the next unused row for this Color box.
		    The internal counter will automatically
		    increment.
		'''

		row = self.next_row

		self.next_row += quantity

		# Make sure that the Color box spans the new row.
		# Remember that rows start at zero, and the quantity
		# of rows starts at one.

		if self.next_row >= self.max_span:
			self.max_span = self.next_row + 1

			self.grid (rowspan=self.max_span)

		return row


	def rowUnTick (self):
		''' Back the row counter up a bit. This is useful if
		    you want to place two distinct Info box entities
		    in the same row, presumably with only one box
		    visible at any given time.
		'''

		if self.next_row == 0:
			raise ValueError, 'no rows exist in this color box'

		self.next_row -= 1

# end of class Color



class Info (Tkinter.Frame):
	''' The Info box serves two purposes: it is a cosmetic widget layered
	    on top of a Color box, and it retains organizational metadata used
	    by sub-widgets. As part of its cosmetic duties, it provides a
	    mouse-over trigger for highlighting any elements visually contained
	    by the box.

	    No sub-widgets use an Info box as a master; rather, they are
	    gridded against the Main.Window, so that all sub-widgets line up
	    nicely.
	'''

	def __init__ (self, colorbox, label, value, button=Button.Status):

		main = colorbox.main

		self.colorbox = colorbox
		self.main     = main
		self.stage    = None

		self.hidden = False

		self.keywords = {}


		Tkinter.Frame.__init__ (self, main.frame,
					background  = kColor.white,
					borderwidth = 2,
					relief	    = Tkinter.GROOVE)

		main.info_boxes.append (self)
		colorbox.boxes.append (self)


		# Establish scale factors and grid positions.

		self.columnconfigure (0, weight=1)
		self.rowconfigure (0, weight=1)

		row = colorbox.rowTick ()

		self.row = row

		self.grid (row=row, column=colorbox.label_column, columnspan=3, padx=5, pady=4, sticky=N+E+S+W)
		main.frame.rowconfigure (row, weight=1)


		# Create the contents of the box.

		# Create a frame to contain the label and sometimes the
		# value (see the Path class).

		self.textbox = Tkinter.Frame (main.frame,
					background  = kColor.white,
					borderwidth = 0,
					relief	    = Tkinter.FLAT)

		self.label = Value.WhiteLabel (master=self.textbox, text=label)

		self.value = value (master=main.frame, box=self, main=main)

		self.label.grid (row=0, column=0, sticky=W)

		self.textbox.columnconfigure (0, weight=1)
		self.textbox.rowconfigure    (0, weight=1)
		self.textbox.rowconfigure    (1, weight=1)

		self.textbox.grid (row=row, column=colorbox.label_column, sticky=S+W, padx=(7,3), pady=6)

		if button == None or button == False:
			self.value.grid (row=row, column=colorbox.value_column, columnspan=2, sticky=S+W, padx=(0,7), pady=6)
			self.button = None

		else:
			self.value.grid (row=row, column=colorbox.value_column, sticky=S+W, pady=6)
			self.button = button (self)

			self.button.grid (row=row, column=colorbox.button_column, sticky=S+E, padx=(3,7), pady=6)

			# Highlight the image button if the cursor enters
			# the box.

			self.bind ('<Enter>', self.createHighlight)
			self.bind ('<Leave>', self.removeHighlight)

			self.textbox.bind ('<Enter>', self.createHighlight)
			self.textbox.bind ('<Leave>', self.removeHighlight)

			self.value.bind ('<Enter>', self.createHighlight)
			self.value.bind ('<Leave>', self.removeHighlight)


	def parameters (self):
		''' Return a list of (label, value, origin, keyword) quartet
		    associated with this Info box. These parameters are
		    used to populate Popup instances.

		    The 'origin' parameter is a string indicating the source
		    of the 'value' parameter. The 'origin' is typically one
		    of 'value' or 'choice'.
		'''

		# Build the one quartet associated with a typical InfoBox.

		label = self.label.get ()
		label = label.split ('\n')[0]

		origin = 'value'

		if hasattr (self, 'value'):
			if hasattr (self.value, 'choice'):
				if self.value.choice != None and \
				   self.value.valid == True:
					value = self.value.choice
					origin = 'choice'
				else:
					value = self.value.value
			else:
				value = self.value.value

			if hasattr (self.value, 'keyword'):
				if self.value.keyword != None:
					keyword = self.value.keyword
				else:
					keyword = None
			else:
				keyword = None
		else:
			value = None
			keyword = None


		# Return the one quartet associated with a typical Info box.

		quartet = (label, value, origin, keyword)
		quartets = (quartet,)

		return quartets


	def update (self):
		''' Pass along requests for components to analyze
		    whether a display update is necessary.
		'''

		if hasattr (self.button, 'update'):
			self.button.update ()

		if hasattr (self.value, 'update'):
			self.value.update ()


	def hide (self, hide=True):
		''' Hide all elements of the Info box.
		'''

		if self.hidden == hide:
			return

		if hasattr (self.button, 'hide'):
			self.button.hide (hide)

		if hide == True:
			self.textbox.grid_remove ()
			self.grid_remove ()

		elif hide == False:
			self.textbox.grid ()
			self.grid ()

		else:
			raise ValueError, 'argument to hide() must be a boolean'

		self.hidden = True


	def reveal (self):
		''' Show all elements of the Info box.
		'''

		return self.hide (False)


	def connect (self):
		''' Enable direct (non-broadcast) keyword activity.
		'''

		try:
			self.value.connect ()
		except AttributeError:
			pass

		try:
			self.button.connect ()
		except AttributeError:
			pass


	def disconnect (self):
		''' Disable any direct (non-broadcast) keyword activity
		    until further notice.
		'''

		try:
			self.value.disconnect ()
		except AttributeError:
			pass

		try:
			self.button.disconnect ()
		except AttributeError:
			pass


	def createHighlight (self, *ignored):
		''' Highlight an image, if any.
		'''

		try:
			self.button.createHighlight ()
		except AttributeError:
			pass

		try:
			self.value.createHighlight ()
		except AttributeError:
			pass


	def removeHighlight (self, *ignored):
		''' Remove highlight on an image, if any.
		'''

		try:
			self.button.removeHighlight ()
		except AttributeError:
			pass

		try:
			self.value.removeHighlight ()
		except AttributeError:
			pass


# end of class Info



class Path (Info):
	''' Same as an Info box, just with a Button.Path as the default
	    button instead of a Button.Status.
	'''

	def __init__ (self, colorbox, label, value, button=Button.Path):

		Info.__init__ (self, colorbox, label, value, button)


		# Because the Button.Path is taller, grid the value
		# underneath the label instead of having it sit
		# alongside.

		# Note that we are also shifting the value from being
		# a component of MainWidow.frame to instead being a
		# component of Path.textbox; this ensures that the
		# overall gridding is consistent.

		self.value.grid (in_=self.textbox, row=1, column=0, padx=0, pady=0, sticky=W)

		# The textbox should now span two columns, which
		# preserves tighter gridding if Info box and Path box
		# elements are mixed in the same column.

		self.textbox.grid (columnspan=2)


# end of class Path



class Bulb (Info):
	''' Same as an Info box, just with a Button.Bulb as the default
	    button instead of a Button.Status.
	'''

	def __init__ (self, colorbox, label, value, button=Button.Bulb):

		Info.__init__ (self, colorbox, label, value, button)


# end of class Bulb



class Ordinal (Info):
	''' An Ordinal box is used to modify RON or PEN mappings for
	    a stage. There is no displayed Value, and the popup button
	    triggers an Popup.Ordinal instead of a Popup.Detail.
	'''

	def __init__ (self, colorbox, label, button=Button.Ordinal):

		Info.__init__ (self, colorbox, label, Value.Label, button)

		# Don't need or want the value.

		self.value.grid_remove ()
		self.value = None


	def ordinals (self, modify):
		''' Indicate to the affliliated popup (if any) that
		    modification of ordinals is enabled/disabled.
		'''

		if modify != True and modify != False:
			raise ValueError, 'argument to Ordinal.ordinals() must be a boolean'

		if self.button.popped != None:
			self.button.popped.ordinals (modify)


# end of class Ordinal
