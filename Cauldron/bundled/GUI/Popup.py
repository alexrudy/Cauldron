import version
version.append ('$Revision: 90095 $')
del version


import ktl
import tkFileDialog
import Tkinter
from Tkinter import N, E, S, W
import traceback

import Box
import Button
import Color
import Event
import Images
import Icon
import Log
import Monitor
import Stage
import Value


class Detail:

	def __init__ (self, popper, service, skip=()):

		if service == None:
			raise ValueError, 'setService() must be invoked for a Button if it will be activated'

		self.callbacks = []

		self.popper = popper
		self.main   = popper.main
		self.stage  = popper.box.stage

		self.service = service
		self.skip = skip

		main  = self.main
		stage = self.stage

		self.top = Tkinter.Toplevel (main.top)

		# Make the overall window re-sizeable.

		self.top.rowconfigure	 (0, weight = 1)
		self.top.columnconfigure (0, weight = 1)

		# Retain a local notion of icon size, which plays into
		# the machinery prompting the Button and Value objects
		# to resize themselves whenever the user increases the
		# font/icon size in the GUI.

		self.icon_size = main.icon_size

		# Create a frame to house the popup contents.

		self.frame = Tkinter.Frame (self.top, background=Color.white)

		rows	= Tkinter.Frame (self.frame, background=Color.white)
		buttons = Tkinter.Frame (self.frame, background=Color.white)

		self.rows    = rows
		self.buttons = buttons
		self.icons   = []
		self.values  = []

		self.frame.grid (sticky=N+E+S+W)

		rows.grid    (row=0, column=0, columnspan=5, sticky=N+E+S+W)
		buttons.grid (row=1, column=0, columnspan=5, sticky=N+W)

		# Enable re-sizing.

		self.frame.columnconfigure (0, weight=1)
		self.frame.rowconfigure (0, weight=1)
		self.frame.rowconfigure (1, weight=0)

		# rowconfigure () is invoked by self.addRow ().

		self.rows.columnconfigure (0, weight=0)
		self.rows.columnconfigure (1, weight=0)
		self.rows.columnconfigure (2, weight=1, minsize=100)

		# Don't shift around the buttons.

		self.buttons.columnconfigure (0, weight=0)
		self.buttons.columnconfigure (1, weight=0)
		self.buttons.columnconfigure (2, weight=0)
		self.buttons.rowconfigure (0, weight=0)
		self.buttons.rowconfigure (1, weight=0)

		self.top.bind ('<Destroy>', self.cleanup)
		self.top.bind ('<Control-KeyPress-w>', self.destroy)
		self.top.bind ('<Control-KeyPress-W>', self.destroy)

		self.row = 0

		self.addRows ()
		self.addButtons ()


	def stopMotion (self):
		''' Stop this stage.
		'''

		Stage.stop (self.stage, self.service)


	def calibrate (self, *ignored):
		''' Calibrate this stage.
		'''

		Stage.calibrate (self.stage, self.service, force=True)


	def lock (self, *ignored):
		''' Call up the lock popup.
		'''

		popup = Lock (self.main, self.stage)


	def unlock (self, *ignored):
		''' Unlock this stage.
		'''

		keyword = self.service['%sLCK' % (self.stage)]

		keyword.write ('', wait=False)


	def toggleMotor (self, *ignored):
		''' If the motor is currently off, turn it on.
		    If it is on, turn it off.
		'''

		toggle = self.service['%sMOO' % (self.stage)]

		try:
			label = self.motor_button['text']

		except Tkinter.TclError:
			# The button disappeared. Not supposed to happen,
			# since someone must have just interactively
			# activated the button.
			return


		# The button label is either 'Turn motor on' or
		# 'Turn motor off'.

		action = label[-3:]
		action = action.strip ()

		toggle.write (action, wait=False)


	def destroy (self, *ignored):
		''' Wrapper to top-level destroy.
		'''

		self.top.destroy ()


	def cleanup (self, *ignored):
		''' Clean shutdown.
		'''

		if hasattr (self.popper, 'popped'):
			self.popper.popped = None

		if hasattr (self, 'callbacks'):
			for keyword, callback in self.callbacks:
				keyword.callback (callback, remove=True)


	def addRows (self):

		stage = self.stage

		self.addRow ('state:',		"%sSTA" % (stage))
		self.addRow ('mode:',		"%sMOD" % (stage), Value.ArbitraryMenu)
		self.addRow ('position: (NAM)',	"%sNAM" % (stage))
		self.addRow ('position: (EAN)',	"%sEAN" % (stage), units=True)
		self.addRow ('position: (ENC)',	"%sENC" % (stage), units=True)
		self.addRow ('position: (RAW)',	"%sRAW" % (stage), Value.Entry)
		self.addRow ('position: (VAL)',	"%sVAL" % (stage), Value.Entry)
		self.addRow ('position: (VAX)',	"%sVAX" % (stage), Value.Entry)
		self.addRow ('position: (VL2)',	"%sVL2" % (stage), Value.Entry)
		self.addRow ('position: (VX2)',	"%sVX2" % (stage), Value.Entry)
		self.addRow ('relative move:',	"%sREL" % (stage), Value.Entry)
		self.addRow ('speed:',		"%sSPD" % (stage), Value.Entry)
		self.addRow ('motor:',		"%sMOO" % (stage), Value.ArbitraryMenu)
		self.addRow ('position: (POS)',	"%sPOS" % (stage), Value.ArbitraryMenu)
		self.addRow ('target:',		"%sTRG" % (stage))
		self.addRow ('torque:',		"%sTOR" % (stage), units=True)
		self.addRow ('pos diff: (CED)',	"%sCED" % (stage), units=True)
		self.addRow ('pos err: (GTE)',	"%sGTE" % (stage))
		self.addRow ('limit:',		"%sLIM" % (stage))
		self.addRow ('locked:',		"%sLCK" % (stage))
		self.addRow ('disabled?:',	"%sXMV" % (stage), Value.XMVLabel)
		self.addRow ('error:',		"%sERR" % (stage), Value.ERRLabel)
		self.addRow ('',		"%sERM" % (stage))
		self.addRow ('message:',	"%sMSG" % (stage), Value.MSGLabel)


	def addRow (self, label, keyword, value_type=Value.Label, units=None):
		''' Add a row to the displayed elements. If the keyword
		    does not exist in the service, that row will not be
		    displayed.
		'''

		if isinstance (keyword, ktl.Keyword):
			name = keyword['name']

		elif keyword in self.service:
			name = keyword
			keyword = self.service[name]

		else:
			return

		for suffix in self.skip:
			if name[-len (suffix):] == suffix:
				return

		prefix = keyword['name'][:-3]
		suffix = keyword['name'][-3:]

		image = Icon.Status (self.rows, self.main)
		label = Value.WhiteLabel (self.rows, text=label)

		value_frame = Tkinter.Frame (self.rows, background=Color.white)

		value = value_type (value_frame, main=self.main, top=self.top)
		value.grid (row=0, column=0, sticky=Tkinter.W)

		self.icons.append (image)
		self.values.append (value)

		# Adjust Value.Entry objects with keyword units, if available.

		try:
			keyword_units = keyword['units']
		except:
			keyword_units = None

		if keyword_units == '':
			keyword_units = None

		if keyword_units != None and \
		   units != False and \
		   (value_type == Value.Entry or units == True):

			units = Value.WhiteLabel (value_frame, text=keyword_units)

			units.grid (row=0, column=1, sticky=N+E+S+W)

		image.grid (column=0, row=self.row)
		label.grid (column=1, row=self.row, sticky=E)
		value_frame.grid (column=2, row=self.row, sticky=W)

		self.frame.rowconfigure (self.row, weight = 1)

		self.row += 1

		value.setKeyword (keyword)

		# setKeyword may initiate a pending change to the menu,
		# if the keyword is an enumerated type. Since that's the
		# only keyword type that has a menu in a Detail popup,
		# it's a safe bet that we now need to request a redraw.

		if value_type == Value.ArbitraryMenu:
			value.redraw ()

		# For any stage that has an override for the default
		# motor-hold-after-a-move behavior, make sure that the
		# Icon.Status for the MOO keyword is updated appropriately.

		if suffix == 'MOO':
			if self.popper.motor_hold != None:
				image.setMotorHold (self.popper.motor_hold)

			# Allow the MOE keyword to override any fixed value
			# for the default motor hold behavior.

			moe = prefix + 'MOE'

			try:
				moe = self.service[moe]
			except KeyError:
				pass
			else:
				moe.callback (image.receiveCallback)

				if moe['monitored'] == True:
					image.receiveCallback (moe)
				else:
					Monitor.queue (moe)


		# If this is the REL keyword, request that the entry box
		# not clear its value when the 'go' button is activated.

		if suffix == 'REL':
			value.setKeepChoice (True)

		keyword.callback (value.receiveCallback)
		keyword.callback (image.receiveCallback)

		self.callbacks.append ((keyword, value.receiveCallback))
		self.callbacks.append ((keyword, image.receiveCallback))

		# If the keyword is already monitored somewhere else,
		# we won't get a "priming" read. If this is the case,
		# pass the existing KTL.Keyword to the appropriate
		# callback mechanisms.

		if keyword['monitored'] == True:
			value.receiveCallback (keyword)
			image.receiveCallback (keyword)
		else:
			Monitor.queue (keyword)


	def addButtons (self):

		buttons = self.buttons
		service = self.service
		stage = self.stage

		column = 0

		keyword = '%sSTP' % (stage)

		if keyword in service:

			keyword = service[keyword]

			self.stop_button = Button.Text (buttons, self.main,
						background=Color.selection)

			self.stop_button['activebackground'] = Color.invalid
			self.stop_button['command'] = self.stopMotion
			self.stop_button['text'] = 'Stop motion'

			self.stop_button.grid (row=1, column=column, sticky=N+E+S+W, padx=1, pady=1)

			column += 1


		keyword = '%sCAL' % (stage)

		if keyword in service:

			keyword = service[keyword]

			self.calibrate_button = Button.Text (buttons, self.main)
			self.calibrate_button['command'] = self.calibrate
			self.calibrate_button['text'] = 'Calibrate'

			self.calibrate_button.grid (row=1, column=column, sticky=N+E+S+W, padx=1, pady=1)

			column += 1

			keyword.callback (self.checkCalibrateButton)
			self.callbacks.append ((keyword, self.checkCalibrateButton))

			Monitor.queue (keyword)

			# Prime the callback, in case it is already being
			# monitored elsewhere.

			self.checkCalibrateButton (keyword)



		keyword = '%sLCK' % (stage)

		if keyword in service:

			keyword = service[keyword]

			self.lock_button = Button.Text (buttons, self.main)
			self.lock_button['command'] = self.lock
			self.lock_button['text'] = 'Lock'

			self.lock_button.grid (row=1, column=column, sticky=N+E+S+W, padx=1, pady=1)

			column += 1

			keyword.callback (self.checkLockButton)
			self.callbacks.append ((keyword, self.checkLockButton))

			Monitor.queue (keyword)

			# Prime the callback, in case it is already being
			# monitored elsewhere.

			self.checkLockButton (keyword)



		# Second row of buttons.

		last_column = column - 1
		column = 0

		keyword = '%sMOO' % (stage)

		if keyword in service:

			keyword = service[keyword]

			self.motor_button = Button.Text (buttons, self.main)
			self.motor_button['command'] = self.toggleMotor
			self.motor_button['text'] = 'Turn motor off'

			self.motor_button.grid (row=2, column=column, sticky=N+E+S+W, padx=1, pady=1)
			column += 1

			keyword.callback (self.checkMotorButton)
			self.callbacks.append ((keyword, self.checkMotorButton))

			Monitor.queue (keyword)

			# Prime the callback, in case it is already being
			# monitored elsewehre.

			self.checkMotorButton (keyword)



		# Last button in the row.

		self.quit_button = Button.Text (buttons, self.main)
		self.quit_button['command'] = self.destroy
		self.quit_button['text'] = 'Close'

		if last_column > column:
			column = last_column

		self.quit_button.grid (row=2, column=column, sticky=N+E+S+W, padx=1, pady=1)


	def checkCalibrateButton (self, keyword):
		''' Adjust the label on the calibrate button depending on the
		    state of the CAL keyword.
		'''

		if keyword['populated'] == True:
			value = keyword['ascii'].lower ()
		else:
			value = None

		if value == 'homed':
			label = 'Re-calibrate'
		else:
			label = 'Calibrate'

		Event.queue (Event.tkSet, self.calibrate_button, 'text', label)


	def checkLockButton (self, keyword):
		''' Adjust the label on the lock button depending on the
		    state of the LCK keyword.
		'''

		if keyword['populated'] == True:
			value = keyword['ascii'].lower ()
		else:
			value = None

		if value == 'unlocked' or value == '':
			label = 'Lock'
			command = self.lock
		else:
			label = 'Unlock'
			command = self.unlock

		Event.queue (Event.tkSet, self.lock_button, 'text', label)
		Event.queue (Event.tkSet, self.lock_button, 'command', command)


	def checkMotorButton (self, keyword):
		''' Adjust the label on the motor on/off button depending on
		    the state of the MOO keyword.
		'''

		if keyword['populated'] == True:
			value = keyword['ascii'].lower ()
		else:
			value = None

		if value == 'on' or value == '':
			label = 'Turn motor off'
		else:
			label = 'Turn motor on'

		Event.queue (Event.tkSet, self.motor_button, 'text', label)


	def title (self, title=None):
		''' Wrapper to the toplevel title() method.
		'''

		if title == None:
			return self.top.title ()

		return self.top.title (title)


	def setSize (self, size=None):

		changed = False

		if hasattr (self.main, 'icon_size') and \
		   self.main.icon_size != self.icon_size:

			self.icon_size = self.main.icon_size
			changed = True

		return changed


	def update (self, *ignored):

		changed = self.setSize ()

		if changed == True:

			for icon in self.icons:
				icon.setSize ()
				icon.redraw ()

			for value in self.values:
				value.update ()


	def connect (self):
		''' Enable direct (non-broadcast) keyword activity.
		'''

		if hasattr (self, 'calibrate_button'):
			Event.tkSet (self.calibrate_button, 'state', Tkinter.NORMAL)


	def disconnect (self):
		''' Disable any direct (non-broadcast) keyword activity
		    until further notice.
		'''

		if hasattr (self, 'calibrate_button'):
			Event.tkSet (self.calibrate_button, 'state', Tkinter.DISABLED)


# end of class Detail



class Omega (Detail):

	def addRows (self):

		if self.popper.power != None:
			self.addRow ('controller power:', self.popper.power, Value.ArbitraryMenu)

		self.addRow ('controller status:', 'DISPSTA')
		self.addRow ('temperature:',	   'TEMP')
		self.addRow ('setpoint:',	   'SETPOINT', Value.Entry)


	def addButtons (self):

		buttons = self.buttons
		column = 0

		self.quit_button = Button.Text (buttons, self.main)
		self.quit_button['command'] = self.destroy
		self.quit_button['text'] = 'Close'

		self.quit_button.grid (row=1, column=column, sticky=N+E+S+W, padx=1, pady=1)


# end of class Omega



class OrdinalEntry (Value.Entry):

	def __init__ (self, popup):

		Value.Entry.__init__ (self, master=popup.rowframe, top=popup.top, go=False, arrows=False)

		self.popup = popup


	def choose (self, choice):

		Value.Entry.choose (self, choice)

		self.popup.checkButtons ()


# end of class OrdinalEntry



class Ordinal:

	def __init__ (self, popper, service):

		self.service = service

		self.popper = popper
		self.main = popper.main
		self.stage = popper.box.stage
		self.keyword = popper.keyword
		self.background = popper.box.colorbox['background']

		background = self.background

		main = self.main


		if hasattr (main, 'modify_ordinals'):
			self.modify_ordinals = main.modify_ordinals

		else:
			self.modify_ordinals = False


		self.top = Tkinter.Toplevel (main.top)

		self.top.bind ('<Destroy>', self.cleanup)
		self.top.bind ('<Control-KeyPress-w>', self.destroy)
		self.top.bind ('<Control-KeyPress-W>', self.destroy)

		suffix = self.keyword['name'][-3:].upper ()

		# Make the overall window re-sizeable.

		self.top.rowconfigure	 (0, weight = 1)
		self.top.columnconfigure (0, weight = 1)

		# Create a frame to house the popup contents.

		self.frame = Tkinter.Frame (self.top, background=background)

		# An internal notion of whether write activity is enabled.

		self.online = True

		self.frame.grid (sticky=N+E+S+W)

		# Enable re-sizing.

		self.frame.columnconfigure (0, weight = 1)
		self.frame.columnconfigure (1, weight = 1, minsize=50)
		self.frame.columnconfigure (2, weight = 1)

		self.frame.rowconfigure (0, weight = 1)
		self.frame.rowconfigure (1, weight = 1, minsize=10)
		self.frame.rowconfigure (2, weight = 0)
		self.frame.rowconfigure (3, weight = 0)


		self.title ("Update %s positions" % (self.stage))

		self.row = 0

		# A box to contain the rows, so that buttons can go at the
		# bottom, and will stay there when we need to add or
		# decrease the number of rows.

		rowframe = Tkinter.Frame (self.frame, background=background)
		rowframe.grid (row=0, column=0, sticky=N+E+S+W, columnspan=3)

		self.rowframe = rowframe

		# Enable re-sizing.

		self.rowframe.columnconfigure (0, weight = 1)
		self.rowframe.columnconfigure (1, weight = 1)
		self.rowframe.columnconfigure (2, weight = 1)
		self.rowframe.columnconfigure (3, weight = 1)

		# Create some rows. Start with labels.

		self.rows = []
		self.positions = 0

		suffix = self.keyword['name'][-3:].upper ()

		if suffix == 'RON':
			self.raw_label = Value.ColorLabel (self.rowframe,
							text='Encoder',
							background=background)

			self.ord_label = Value.ColorLabel (self.rowframe,
							text='Ordinal',
							background=background)

			self.nam_label = Value.ColorLabel (self.rowframe,
							text='Name',
							background=background)

			self.raw_label.grid (row=self.row, column = 0)
			self.ord_label.grid (row=self.row, column = 1)
			self.nam_label.grid (row=self.row, column = 2)

			# Add a tuple to self.rows as a placeholder for
			# the labels.

			self.rows.append ((None, None, None))


		elif suffix == 'PEN':
			self.pos_label = Value.ColorLabel (self.rowframe,
							text='Position',
							background=background)

			self.nam_label = Value.ColorLabel (self.rowframe,
							text='Name',
							background=background)

			self.pos_label.grid (row=self.row, column = 0)
			self.nam_label.grid (row=self.row, column = 1)

			# Add a tuple to self.rows as a placeholder for
			# the labels.

			self.rows.append ((None, None))


		self.rowframe.rowconfigure (self.row, weight=1)

		self.row += 1

		# Put buttons on the window to make it do things.

		self.add_button   = Button.Text (self.frame, main)
		self.quit_button  = Button.Text (self.frame, main)
		self.reset_button = Button.Text (self.frame, main)
		self.write_button = Button.Text (self.frame, main)

		self.add_button['text']   = 'Add Row'
		self.quit_button['text']  = 'Close'
		self.reset_button['text'] = 'Reset'
		self.write_button['text'] = 'Write All'

		self.add_button['command']   = self.addRow
		self.quit_button['command']  = self.destroy
		self.reset_button['command'] = self.clearChoices
		self.write_button['command'] = self.write

		self.reset_button['state'] = Tkinter.DISABLED
		self.write_button['state'] = Tkinter.DISABLED

		if self.modify_ordinals == False:
			self.add_button['state'] = Tkinter.DISABLED

		self.reset_button.grid (row=2, column=0, sticky=W+E, padx=1, pady=1)
		self.write_button.grid (row=3, column=0, sticky=W+E, padx=1, pady=1)

		self.add_button.grid   (row=2, column=2, sticky=W+E, padx=1, pady=1)
		self.quit_button.grid  (row=3, column=2, sticky=W+E, padx=1, pady=1)


		# Set up the callback for new values.

		self.setCallback (self.keyword)

		# Invoke the callback once explicitly in order
		# to prime the display, just in case the keyword
		# was already being monitored.

		self.receiveCallback (self.keyword)


	def destroy (self, *ignored):
		''' Wrapper to top-level destroy.
		'''

		self.top.destroy ()


	def cleanup (self, *ignored):
		''' Clean shutdown.
		'''

		self.keyword.callback (self.receiveCallback, remove=True)

		if hasattr (self.popper, 'popped'):
			self.popper.popped = None


	def loseFocus (self):
		''' Wrapper to the loseFocus method on any component
		    entry boxes.
		'''

		for row in self.rows:
			for field in row:
				if hasattr (field, 'focused'):
					pass
				else:
					continue

				if field.focused:
					field.loseFocus ()


	def connect (self):
		''' Enable direct (non-broadcast) keyword activity.
		'''

		self.online = True

		self.checkButtons ()


	def disconnect (self):
		''' Disable any direct (non-broadcast) keyword activity
		    until further notice.
		'''

		self.online = False

		self.checkButtons ()


	def setCallback (self, keyword):
		''' Set up this Value object to receive callbacks
		    from the specified ktl.Keyword object. setCallback ()
		    will also establish monitoring of the ktl.Keyword
		    if necessary.
		'''

		keyword.callback (self.receiveCallback)
		Monitor.queue (keyword)


	def receiveCallback (self, keyword):
		''' Accept the ktl.Keyword callback, queueing up appropriate
		    events for later execution.
		'''

		if keyword['populated'] == False:
			return

		try:
			value = keyword['ascii']
		except:
			return


		suffix = keyword['name'][-3:].upper ()

		if suffix == 'RON':
			Event.queue (self.updateRON, value)
		elif suffix == 'PEN':
			Event.queue (self.updatePEN, value)
		else:
			raise ValueError, "unhandled keyword suffix '%s' for Popup.Ordinal callback" % (suffix)


	def updatePEN (self, value):
		''' Update the visible display of the popup to reflect the
		    new PEN value.
		'''

		self.loseFocus ()

		pairs = Stage.parsePEN (value)

		# If the new PEN value has fewer defined positions than the
		# old one, we need to reduce the number of displayed rows.

		# There is a dummy row in self.rows.

		if len (pairs) < len (self.rows) - 1:

			while len (pairs) != len (self.rows) - 1:

				self.removeLastRow ()

		# If the new PEN value has more defined positions than the
		# old one, the loop below will add as many rows as are
		# necessary to represent the quantity of positions defined.

		for index in range (len (pairs)):
			pair = pairs[index]

			# The zero'th row is a place-holder row for the
			# labels.

			row_index = index + 1

			try:
				row = self.rows[row_index]
			except IndexError:
				row = None

			if row == None:
				self.addRow (position = pair[0],
					     name     = pair[1])
			else:
				# The displayed values are in
				# Position/Name order.

				old_pos = row[0].value
				old_nam = row[1].value

				new_pos = pair[0]
				new_nam = pair[1]

				if new_pos != old_pos:
					row[0].setChoice (None)
					row[0].set (pair[0])
					row[0].redraw ()
				if new_nam != old_nam:
					row[1].setChoice (None)
					row[1].set (pair[1])
					row[1].redraw ()

		self.positions = len (pairs)

		self.checkButtons ()


	def updateRON (self, value):
		''' Update the visible display of the popup to reflect the
		    new RON value.
		'''

		self.loseFocus ()

		triplets = Stage.parseRON (value)

		# If the new RON value has fewer defined positions than the
		# old one, we need to reduce the number of displayed rows.

		# There is a dummy row in self.rows.

		if len (triplets) < len (self.rows) - 1:

			while len (triplets) != len (self.rows) - 1:

				self.removeLastRow ()

		# If the new RON value has more defined positions than the
		# old one, the loop below will add as many rows as are
		# necessary to represent the quantity of positions defined.

		for index in range (len (triplets)):
			triplet = triplets[index]

			# The zero'th row is a place-holder row for the
			# labels.

			row_index = index + 1

			try:
				row = self.rows[row_index]
			except IndexError:
				row = None

			if row == None:
				self.addRow (encoder = triplet[0],
					     ordinal = triplet[1],
					     name    = triplet[2])
			else:
				# The displayed values are in
				# Encoder/Ordinal/Name order.

				old_raw = row[0].value
				old_ord = row[1].value
				old_nam = row[2].value

				new_raw = triplet[0]
				new_ord = triplet[1]
				new_nam = triplet[2]

				if new_raw != old_raw:
					row[0].setChoice (None)
					row[0].set (triplet[0])
					row[0].redraw ()
				if new_ord != old_ord:
					row[1].setChoice (None)
					row[1].set (triplet[1])
					row[1].redraw ()
				if new_nam != old_nam:
					row[2].setChoice (None)
					row[2].set (triplet[2])
					row[2].redraw ()

		self.positions = len (triplets)

		self.checkButtons ()


	def addRow (self, encoder=None, ordinal=None, name=None, position=None):
		''' Add a row to the display.
		'''

		# Check to see how many fields this row needs, based on
		# how many slots there are in the 0th (label) row.

		label_row = self.rows[0]

		fields = len (label_row)

		new_row = []


		remove_function = self.removeSpecificRow (self.row)

		remove_button = Button.Simple (self.rowframe, self.main, fontsized=True)

		remove_button.setImage (Images.get ('error'))
		remove_button.redraw ()
		remove_button['command'] = remove_function


		for value in range (fields):
			new_row.append (OrdinalEntry (self))

		new_row.append (remove_button)


		if fields == 3:
			new_row[0].set (encoder)
			new_row[1].set (ordinal)
			new_row[2].set (name)

			new_row[0].redraw ()
			new_row[1].redraw ()
			new_row[2].redraw ()

			# Widen the 'name' field, and make it left-justified.

			new_row[2].display['width'] = 30
			new_row[2].display['justify'] = Tkinter.LEFT

			if self.modify_ordinals == False:
				new_row[0].disable ()
				new_row[1].disable ()

		elif fields == 2:
			new_row[0].set (position)
			new_row[1].set (name)

			new_row[0].redraw ()
			new_row[1].redraw ()

			# Widen the 'name' field, and make it left-justified.

			new_row[1].display['width'] = 30
			new_row[1].display['justify'] = Tkinter.LEFT

			if self.modify_ordinals == False:
				new_row[0].disable ()

		# Note that the following grid options are also set in
		# removeRow ().

		column = 0

		for field in new_row:

			if column == len (new_row) - 1:
				# The last component of the row is the remove
				# button.

				field.grid (row=self.row, column=column, sticky=W, padx=2, pady=1)

				if self.modify_ordinals == False:
					field.grid_remove ()

			else:
				# This is not the last component of the row.

				field['background'] = self.background
				field.grid (row=self.row, column=column, sticky = N+E+S+W)

			column = column + 1

		self.rowframe.rowconfigure (self.row, weight = 1)

		self.row += 1

		self.rows.append (new_row)

		self.checkButtons ()


	def removeSpecificRow (self, index):
		''' Function generator to use self.removeRow ()
		    on buttons.
		'''

		function = lambda : self.removeRow (index)

		return function


	def removeRow (self, index):
		''' Remove a row from the display. Its values are
		    forgotten.
		'''

		row = self.rows[index]

		# Slice out that row.

		self.rows = self.rows[:index] + self.rows[index + 1:]

		self.row -= 1

		# Eliminate it from the display.

		for field in row:
			field.grid_forget ()

		row = None

		# Re-grid the rows following the one that was removed.

		current_row = index

		for row in self.rows[index:]:

			column = 0
			for field in row:

				if column == len (row) - 1:
					# The last component of the row is the remove
					# button.

					field.grid (row=current_row, column=column, sticky=W, padx=2, pady=1)

				else:
					# Not the last component of the row.
					field.grid (row=current_row, column=column, sticky = N+E+S+W)

				column = column + 1


			# The removal button needs a new function for the
			# proper row index.

			remove_function = self.removeSpecificRow (current_row)
			row[-1]['command'] = remove_function

			current_row += 1

		self.checkButtons ()


	def removeLastRow (self):

		row = self.rows.pop ()
		self.row -= 1

		for field in row:
			field.grid_forget ()

		row = None

		self.checkButtons ()


	def checkButtons (self):
		''' See whether the buttons should be enabled or disabled.
		    If there is user input, they should be enabled,
		    Otherwise, disabled.
		'''

		enabled = False

		# self.rows contains a dummy row.

		if self.positions != len (self.rows) - 1:
			enabled = True
		else:
			for row in self.rows:
				if enabled == True:
					break

				for field in row:
					if enabled == True:
						break

					if hasattr (field, 'choice'):
						pass
					else:
						continue

					if field.choice != None:
						enabled = True


		# What state should the buttons be in?

		if enabled == True:
			reset_state = Tkinter.NORMAL
		else:
			reset_state = Tkinter.DISABLED

		if enabled == True and self.online == True:
			write_state = Tkinter.NORMAL
		else:
			write_state = Tkinter.DISABLED

		Event.tkSet (self.reset_button, 'state', reset_state)
		Event.tkSet (self.write_button, 'state', write_state)


	def clearChoices (self):
		''' Clear all choices. Basically, re-build the display.
		'''

		# First, clear any choices.

		for row in self.rows:
			for field in row:
				if hasattr (field, 'choice'):
					pass
				else:
					continue

				if field.choice != None:
					field.choose (None)

				if field.focused:
					field.loseFocus ()

		# Next, re-assert that all displayed values
		# (and the quantity of rows) are correct.

		self.receiveCallback (self.keyword)


	def write (self):

		suffix = self.keyword['name'][-3:].upper ()

		if suffix == 'RON':
			self.writeRON ()

		elif suffix == 'PEN':
			self.writePEN ()


	def writePEN (self):
		''' Create and write a new PEN value.
		'''

		values = []

		change_made = False

		# self.rows contains a dummy row.

		if self.positions != len (self.rows) - 1:
			change_made = True

		for row in self.rows:
			pair = []

			for field in row:
				if hasattr (field, 'choice'):
					pass
				else:
					continue

				if field.choice != None and field.choice != field.value:
					change_made = True
					value = field.choice

				elif field.value != None:
					value = field.value

				else:
					value = ''

				pair.append (value)

			if len (pair) < 2 or \
			   pair[0] == '' or pair[0] == None or \
			   pair[1] == '' or pair[1] == None:

				# Null values not allowed.
				pass
			else:
				values.extend (pair)


		# Only write changes if a choice was made.

		if change_made == True:
			self.loseFocus ()

			new_pen = Stage.createPEN (values)

			try:
				self.keyword.write (new_pen)
			except:
				Log.alert ("Unable to write '%s' to %s" % (new_pen, self.keyword['name']))
				ktl.log (ktl.LOG_ERROR, "Error writing '%s' to %s:\n%s" % (new_pen, self.keyword['name'], traceback.format_exc ()))


	def writeRON (self):
		''' Create and write a new RON value.
		'''

		values = []

		change_made = False

		# self.rows contains a dummy row.

		if self.positions != len (self.rows) - 1:
			change_made = True

		for row in self.rows:
			triplet = [None, None, None]

			for field in row:
				if hasattr (field, 'choice'):
					pass
				else:
					continue

				if field.choice != None and field.choice != field.value:
					change_made = True
					value = field.choice
				elif field.value != None:
					value = field.value
				else:
					value = ''

				# This assumes that the fields are
				# arranged in RAW/ORD/NAM order.

				# The check against None is what
				# allows the triplet to be formed
				# in sequence.

				if triplet[0] == None:
					# RAW.
					triplet[0] = value
				elif triplet[1] == None:
					# ORD.
					triplet[1] = value
				else:
					# NAM.
					triplet[2] = value

			if triplet[0] == '' or triplet[0] == None or \
			   triplet[1] == '' or triplet[1] == None or \
			   triplet[2] == '' or triplet[2] == None:

				# Null values not allowed.
				pass
			else:
				values.extend (triplet)

		# Only take change if a choice was made.

		if change_made == True:
			self.loseFocus ()

			new_ron = Stage.createRON (values)

			try:
				self.keyword.write (new_ron)
			except:
				Log.alert ("Unable to write '%s' to %s" % (new_ron, self.keyword['name']))
				ktl.log (ktl.LOG_ERROR, "Error writing '%s' to %s:\n%s" % (new_ron, self.keyword['name'], traceback.format_exc ()))


	def title (self, title=None):
		''' Wrapper to top-level title.
		'''

		if title == None:
			return self.top.title ()

		return self.top.title (title)


	def ordinals (self, value):
		''' Wrapper to enable/disable below.
		'''

		self.modify_ordinals = value

		if value == True:
			self.enableOrdinals ()
			state = Tkinter.NORMAL

		elif value == False:
			self.disableOrdinals ()
			state = Tkinter.DISABLED

		else:
			raise ValueError, 'Popup.Ordinal.ordinals() only accepts a boolean value'

		Event.tkSet (self.add_button, 'state', state)


	def disableOrdinals (self):
		''' Disable modification of ordinal positions in addition
		    to the names affiliated with a position.
		'''

		# Skip the zero'th dummy row.

		rows = self.rows[1:]

		for row in rows:

			# Hide the 'remove' button at the end of the row.
			row[-1].grid_remove ()

			if len (row) == 4:
				# RON row, in Encoder / Ordinal / Name order.
				row[0].disable ()
				row[1].disable ()

			elif len (row) == 3:
				# PEN row, in Position / Name order.
				row[0].disable ()

			else:
				raise ValueError, "bad length (%d) for row in %s popup" % (len (row), self.stage)


	def enableOrdinals (self):
		''' Enable modification of ordinal positions in addition
		    to the names affiliated with a position.
		'''

		# Skip the zero'th dummy row.

		rows = self.rows[1:]

		for row in rows:

			# Restore the 'remove' button at the end of the row.
			row[-1].grid ()

			if len (row) == 4:
				# RON row, in Encoder / Ordinal / Name order.
				row[0].enable ()
				row[1].enable ()

			elif len (row) == 3:
				# PEN row, in Position / Name order.
				row[0].enable ()

			else:
				raise ValueError, "bad length (%d) for row in %s popup" % (len (row), self.stage)


	def update (self, *ignored):
		'''This function is invoked whenever the font size is
		   changed, and a popup window is open.
		'''

		# Skip the zero'th dummy row.

		rows = self.rows[1:]

		for row in rows:

			remove_button = row[-1]
			remove_button.update ()


# end of class Ordinal



class Selection:
	''' The :class:`Selection` class is a base class; it provides the
	    basic structure: a presentation of all components, with their active
	    values. Additional sugar is provided by the sub-classes.
	'''

	def __init__ (self, main, indiscriminate=False):

		self.main = main
		self.icon_size = main.icon_size
		self.indiscriminate = indiscriminate


		# Keep track of all the rows in the popup,
		# so that we can iterate over them later on.

		self.rows = []

		self.top = Tkinter.Toplevel (main.top)

		self.top.bind ('<Control-KeyPress-w>', self.destroy)
		self.top.bind ('<Control-KeyPress-W>', self.destroy)

		self.top['background'] = Color.white

		# Don't bother with allowing resizing. That means we don't
		# have to worry about appropriate rowconfigure() and
		# columnconfigure() calls.

		self.top.resizable (0, 0)

		# Instructions across the top.

		instruction = 'Use a mouse button to select or deselect components.'

		self.instructions = Value.WhiteLabel (self.top, text=instruction)
		self.instructions['anchor'] = W
		self.instructions.grid (row=0, column=0, sticky=N+E+S+W, padx=1, pady=1)


		# Create a frame to house the rows.

		self.frame = Tkinter.Frame (self.top, background=Color.white)
		self.frame.grid (row=1, sticky=N+E+S+W)


		# Separate frame for buttons along the bottom.

		self.buttons = Tkinter.Frame (self.top, background=Color.white)
		self.buttons.grid (row=2, column=0, sticky=E+N)

		self.buttons.columnconfigure (0, weight=0)
		self.buttons.columnconfigure (1, weight=0)
		self.buttons.columnconfigure (2, weight=0)
		self.buttons.rowconfigure (0, weight=0)


		# Mimic the structure of the main window.

		self.color_boxes = []

		for box in main.color_boxes:
			background = box['background']

			columns = len (self.color_boxes)

			newbox = Box.Color (self, background=background)

			# We're using the zero'th grid row for instructions.

			newbox.grid (row=1)

			# Keep track of the SelectRows in each Color box.

			newbox.rows = []



		# Go through each of the color boxes present in the
		# main view, and replicate that information here.

		main.popupStructure (self)


		# Put buttons along the bottom to assist in selecting groups
		# of components.

		self.toggle_button = Button.Text (self.buttons, self.main)
		self.action_button = Button.Text (self.buttons, self.main)
		self.cancel_button = Button.Text (self.buttons, self.main)

		self.toggle_button['text'] = 'Select all'
		self.action_button['text'] = 'Do something'
		self.cancel_button['text'] = 'Cancel'

		self.toggle_button['command'] = self.toggleAll
		self.cancel_button['command'] = self.destroy

		self.toggle_button.grid (row=0, column=0, sticky=N+E+S+W, padx=3, pady=1)
		self.action_button.grid (row=0, column=1, sticky=N+E+S+W, padx=3, pady=1)
		self.cancel_button.grid (row=0, column=2, sticky=N+E+S+W, padx=3, pady=1)


	def selectOne (self, stage):
		''' Iterate through all available SelectRows; select any
		    rows matching 'stage', and unselect any not matching.
		'''

		for row in self.rows:

			if row.stage != stage and row.selected:
				row.toggle ()
			elif row.stage == stage and row.selected == False:
				row.toggle ()


	def toggle (self, box, selection):
		''' Switch the rows in the designated box between selected
		    and unselected.
		'''

		for row in box.rows:
			if selection == True and row.selected == False:
				row.toggle ()

			elif selection == False and row.selected == True:
				row.toggle ()

			# else no action required.


	def toggleAll (self):

		if self.toggle_button['text'] == 'Unselect all':
			value = False
		else:
			value = True

		for box in self.color_boxes:
			self.toggle (box, value)

		# The act of toggling a row will trigger a check
		# for the label on the select/unselect button.


	def allSelected (self):
		''' Returns True if all the SelectRows are selected.
		'''

		for row in self.rows:
			if row.selected == False:
				return False

		return True


	def noneSelected (self):
		''' Returns True if none of the SelectRows in the entire popup
		    are selected.
		'''

		for row in self.rows:
			if row.selected == True:
				return False

		return True


	def checkButtons (self, box=None):
		''' Check the select/unselect all button for appropriate
		    labelling, on each color box if no box is specified.
		'''

		select_text = 'Select all'
		unselect_text = 'Unselect all'

		try:
			button = self.toggle_button
		except AttributeError:
			# The toggle button doesn't exist yet. It's possible
			# that the caller invoked toggle() while initializing
			# a popup.
			return

		if self.allSelected ():
			Event.tkSet (button, 'text', unselect_text)
		else:
			Event.tkSet (button, 'text', select_text)


	def destroy (self, *ignored):
		''' Wrapper to top-level destroy.
		'''

		self.top.destroy ()


# end of class Selection



class SelectRow (Tkinter.Frame):

	def __init__ (self, popup, colorbox, label, keyword, value, stage):

		# By default, we are selected.

		self.selected = True
		relief = Tkinter.SUNKEN
		color = Color.selection
		icon = Images.get ('checked')

		Tkinter.Frame.__init__ (self, popup.frame,
					background  = color,
					borderwidth = 1,
					relief	    = relief)

		# Establish scale factors.

		self.columnconfigure (0, weight = 1)
		self.rowconfigure (0, weight = 1)

		row = colorbox.rowTick ()
		column = colorbox.label_column

		self.colorbox = colorbox
		self.main     = popup.main
		self.popup    = popup
		self.stage    = stage

		colorbox.rows.append (self)
		popup.rows.append (self)

		self.row = row

		self.grid (row=row, column=column, columnspan=3, padx=5, pady=4, sticky=N+E+S+W)

		self.keyword = keyword
		self.value = value

		self.origin = None

		self.label  = Value.WhiteLabel (popup.frame, text=label)
		self.choice = Value.WhiteLabel (popup.frame, text=value)
		self.icon   = Icon.Simple (popup.frame, self.main)

		# If a value is 'Unknown' or 'Irregular', mark the row
		# as disabled-- saving 'Unknown' to a setup is pointless.

		# If there is no value associated with a row, mark it as
		# disabled. This would only occur in production if a popup
		# function is invoked while the GUI doesn't have a full set
		# of values available from its KTL services.

		if value == None:
			value = '--'

		lower = value.lower ()

		if lower == 'unknown' or lower == 'irregular' or value == '--':

			if popup.indiscriminate == False:
				self.selected = None
				self.value = None
				color = 'grey'
				Event.tkSet (self, 'relief', Tkinter.FLAT)

				icon = None

		self.icon.setImage (icon)
		self.icon.redraw ()


		if color != Color.white:
			Event.tkSet (self,	  'background', color)
			Event.tkSet (self.label,  'background', color)
			Event.tkSet (self.choice, 'background', color)
			Event.tkSet (self.icon,   'background', color)
			Event.tkSet (self.icon,   'activebackground', color)

		self.label.grid  (row=row, column=column,     sticky=S+E, padx=7, pady=6)
		self.choice.grid (row=row, column=column + 1, sticky=S+E, padx=2, pady=6)
		self.icon.grid	 (row=row, column=column + 2, sticky=S+E, padx=7, pady=6)

		# For active rows, change the cursor to indicate
		# clicking does something, and bind all mouse buttons
		# for selection toggling.

		if self.value != None:

			for widget in (self, self.label, self.choice, self.icon):

				Event.tkSet (widget, 'cursor', 'hand2')

				for button in ('<Button-1>', '<Button-2>', '<Button-3>'):

					widget.bind (button, self.toggle)

	def setOrigin (self, origin):

		if self.origin == origin:
			return False

		self.origin = origin
		return True


	def disable (self, *ignored):
		''' Disable this SelectRow. This is not expected to
		    be reversed, thus, there is no enable () method.
		'''

		self.value = None
		self.selected = None

		Event.tkSet (self,	   'background', 'grey')
		Event.tkSet (self.label,  'background', 'grey')
		Event.tkSet (self.choice, 'background', 'grey')
		Event.tkSet (self.icon,   'background', 'grey')

		Event.tkSet (self.icon, 'activebackground', 'grey')

		Event.tkSet (self, 'relief', Tkinter.FLAT)


		for widget in (self, self.label, self.choice, self.icon):

			Event.tkSet (widget, 'cursor', '')

			widget.unbind ('<Button-1>')
			widget.unbind ('<Button-2>')
			widget.unbind ('<Button-3>')


		changed = self.icon.setImage (None)

		if changed == True:
			self.icon.redraw ()


		# Having revised the state of a SelectRow, make sure
		# that the base Selection instance has the right labels
		# on its buttons.

		if hasattr (self.popup, 'checkButtons'):

			self.popup.checkButtons ()


	def toggle (self, *ignored):
		''' Switch between selected and unselected.
		'''

		if self.value == None:
			return

		# Toggle our status.

		if self.selected == True:
			self.selected = False
			color = Color.white
			image = None
			relief = Tkinter.RAISED

		else:
			self.selected = True
			color = Color.selection
			image = Images.get ('checked')
			relief = Tkinter.SUNKEN

		Event.tkSet (self, 'background', color)
		Event.tkSet (self, 'relief', relief)
		Event.tkSet (self.label, 'background', color)
		Event.tkSet (self.choice, 'background', color)
		Event.tkSet (self.icon, 'background', color)
		Event.tkSet (self.icon, 'activebackground', color)

		self.icon.setImage (image)
		self.icon.redraw ()

		if hasattr (self.popup, 'checkButtons'):

			self.popup.checkButtons (self.colorbox)


# end of class SelectRow



class Lock (Selection):

	def __init__ (self, main, stage=None):

		Selection.__init__ (self, main, indiscriminate=True)

		# Fool the Value.Entry object into thinking this is a
		# 'main window.' The only observable effect is that
		# loseFocus will do the right thing, and re-focus on
		# Selection.top, not Main.Window.top.

		self.frame.icon_size = main.icon_size

		self.top.title ('Select components to lock')


		# Move the existing buttons from the Selection down a row.

		self.buttons.grid (row=3)
		self.top.rowconfigure (3, weight=0)

		# Put in an entry box to acquire the reason for locking.

		self.rationale = Value.Entry (self.top, main=self, go=False, arrows=False)


		self.rationale.display['width'] = 60
		self.rationale.display['relief'] = Tkinter.SUNKEN
		self.rationale.display['justify'] = Tkinter.LEFT
		self.rationale.display['borderwidth'] = 1

		self.rationale.set ('Explain why you are locking the selected components (required)')
		self.rationale.redraw ()

		self.rationale.grid (row=2, sticky=N+W, padx=1, pady=1)

		# Clear non-entered-text when the user clicks into the box.

		self.rationale.display.bind ('<FocusIn>', self.rationaleFocusIn)

		self.action_button['text'] = 'Lock'
		self.action_button['command'] = self.lock


		# If a stage was specified, start with only that stage selected.

		if stage != None:
			self.selectOne (stage)

		# Whenever a choice is made, we need to invoke our
		# checkButtons routine. Using a trace on the
		# StringVar associated with the Value.Entry object
		# does not work, because we care about the choice,
		# not the StringVar value-- and there are no
		# guarantees about which trace call will be invoked
		# first.

		def choose (choice, value=self.rationale, lockpopup=self):
			Value.Entry.choose (value, choice)
			lockpopup.checkButtons ()

		self.rationale.choose = choose

		self.checkButtons ()

		# If an Info box does not reasonably have a LCK keyword
		# associated with it, disable its corrsponding SelectRow.
		# While we're at it, assign the LCK keyword to be the
		# 'active' keyword for the row.

		for row in self.rows:

			lockable = False

			if row.keyword != None:

				# Take the row's keyword name, strip off the
				# suffix, and put LCK in its place.

				keyword = row.keyword['name']
				keyword = '%sLCK' % (keyword[:-3])

				services = self.main.services
				service  = services[row.keyword['service']]

				if keyword in service:
					row.keyword = service[keyword]
					lockable = True


			if lockable == False:
				row.disable ()
				row.keyword = None


	def lock (self, *ignored):
		''' Lock all the selected components.
		'''

		# The rationale will never be None, given that the Lock
		# button is not enabled unless the rationale != None.

		rationale = self.rationale.choice

		locking = []

		for row in self.rows:

			if row.selected == True and row.keyword != None:

				row.keyword.write (rationale, wait=False)

		self.destroy ()


	def checkButtons (self, box=None):
		''' In addition to the per-color selections, adjust the
		    Lock button according to any selections.
		'''

		Selection.checkButtons (self, box)

		# Disable the 'Lock' button if no components are selected, or
		# if no rationale is provided.

		if self.rationale.choice == None	or \
		   self.rationale.choice == ''		or \
		   self.noneSelected ():

			Event.tkSet (self.action_button, 'state', Tkinter.DISABLED)
			Event.tkSet (self.action_button, 'cursor', '')
		else:
			Event.tkSet (self.action_button, 'state', Tkinter.NORMAL)
			Event.tkSet (self.action_button, 'cursor', 'hand2')


	def rationaleFocusIn (self, *ignored):
		''' Binding the focus event appears to clear previous
		    bindings. This is unfortunate, because the Value.Entry
		    widget has important things that happen on focus.

		    Thus, ball up all the desired calls here.
		'''

		self.rationale.focusIn ()
		self.clearRationale ()


	def clearRationale (self, *ignored):
		''' If there is no rationale, clear the displayed text
		    by choosing the empty string. This is triggered when
		    focus enters the entry box.
		'''

		if self.rationale.choice == None:
			self.rationale.choose ('')


# end of class Lock
