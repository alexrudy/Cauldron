import version
version.append ('$Revision: 88318 $')
del version


import ktl
import sys
import threading
import Tkinter
from Tkinter import N, E, S, W
import traceback

import Box
import Color
import Event
import Font
import kImage
import Log
import Monitor
import Popup
import Setups
import Stage


class Window:

	MainWindow = True

	def __init__ (self, width=None, height=None, setups=False, debug=False):

		if debug == True:
			self.debug ()

		self.color_boxes = []
		self.info_boxes = []

		self.service = None
		self.services = {}

		self.everything_ok = False

		self.top = Tkinter.Tk ()


		# Fonts can't be established until Tkinter.Tk() gets invoked.

		Font.initialize ()


		# Debug logfile, enabled via self.debug().

		self.logfile = None


		# Augment the height by 10% to accomodate the menu bar.

		if width != None and height != None:
			self.top.minsize (width, (height + height / 10))

		# Keep a record of the icon size used in this instance.

		self.icon_size = kImage.default_size

		# Make the overall window re-sizeable.

		self.top.rowconfigure	 (0, weight=1)
		self.top.columnconfigure (0, weight=1)

		# Create a frame to house the GUI.
		# Columns are configured by the Box.Color class.

		self.frame = Tkinter.Frame (self.top)

		# Create a frame to contain error messages.

		self.error_frame = Tkinter.Frame (self.top)
		self.error_frame.columnconfigure (0, weight=1)
		self.error_frame.rowconfigure	 (0, weight=1)

		# Grid everything now, so that we don't have to provide
		# any parameters later on for any subsequent grid/remove
		# operations.

		self.error_frame.grid (sticky=N+E+S+W)
		self.error_frame.grid_remove ()

		self.frame.grid (sticky=N+E+S+W)

		# error_text will be set to a non-None value
		# when an error message needs to be front-and-center.
		# The error_severity is the mechanism used internally
		# to figure out which message should be displayed;
		# highest value wins.

		self.error_label = None
		self.error_text = None
		self.error_severity = 0


		# Keep track of heartbeats (these values are also
		# initialized in self.checkHeartbeat()).

		self.heartbeats = {}
		self.heartbeat_ok = {}
		self.heartbeats_ok = True

		# Keep track of dispatcher states, via keyword broadcasts.

		self.dispatcher_state = {}
		self.dispatchers_ok = True

		self.everything_ok = True

		# If desired, put up a separate bar underneath the menu to
		# manipulate setups.

		if setups == True:

			self.setups_bar = Setups.Bar (self)

		self.processMonitorQueue.im_func.active = False
		Monitor.processor (self.processMonitorQueue)


	def destroy (self, *ignored):
		''' Wrapper to the top-level destroy.
		'''

		self.top.destroy ()


	def setError (self, text, severity=None):
		''' Set a given error text, which causes the entire
		    GUI to be hidden. If error is set to None, any
		    existing error is cleared.

		    If the error text is not None, an integer severity
		    for the message needs to be set.
		'''

		# If a severity is set, do not proceed if the severity is
		# lower than the current severity (if any).

		if severity != None:
			severity = int (severity)

			if self.error_severity != None:

				if severity < self.error_severity:
					return

				self.error_severity = severity


		# Reset condition.

		if text == None:
			self.error_severity = 0
			self.error_text = None

			self.error_frame.grid_remove ()
			self.frame.grid ()

			if hasattr (self, 'setups_bar'):
				self.setups_bar.grid ()

			return


		# Is this the same error message we're alreay displaying?

		if text == self.error_text:
			return


		# New error message.

		if self.error_text == None:
			if hasattr (self, 'setups_bar'):
				self.setups_bar.grid_remove ()

			self.frame.grid_remove ()
			self.error_frame.grid ()

		self.error_text = text

		if self.error_label == None:
			self.error_label = Tkinter.Label (self.error_frame,
							foreground='black',
							background=Color.selection,
							font=Font.display,
							justify=Tkinter.CENTER,
							wraplength=400)

			sticky = Tkinter.N + Tkinter.E + Tkinter.S + Tkinter.W
			self.error_label.grid (row=0, column=0, sticky=sticky)

		Event.tkSet (self.error_label, 'text', self.error_text)



	def changeFontSize (self, amount=1):
		''' Adjust all font sizes by the specified number of points.
		    The resulting font size cannot be less than one point.
		'''

		for font in Font.instances ():
			current_size = font.cget ('size')

			new_size = current_size + amount

			if new_size < 1:
				new_size = 1

			if current_size != new_size:
				font.configure (size=new_size)


	def changeIconSize (self, amount=1):
		''' Adjust all icon sizes by the specified number of pixels.
		    The resulting icon size cannot be less than one pixel.
		'''

		new_icon_size = self.icon_size + amount

		if new_icon_size < 1:
			new_icon_size = 1


		if new_icon_size != self.icon_size:

			self.icon_size = new_icon_size

			for box in self.info_boxes:

				Event.queue (box.update)


	def increaseSize (self, *ignored):
		''' Wrapper to self.changeFontSize() and self.changeIconSize.
		'''

		self.changeFontSize (amount=1)
		self.changeIconSize (amount=1)


	def decreaseSize (self, *ignored):
		''' Wrapper to self.changeFontSize() and self.changeIconSize.
		'''

		self.changeFontSize (amount=-1)
		self.changeIconSize (amount=-1)


	def handleResizeEvent (self, event):
		''' Event wrapper to self.increaseSize() and
		    self.decreaseSize().
		'''

		# event.keysym is one of the following values:

		increment_strings = ('plus','equal','KP_Add')
		decrement_strings = ('minus','KP_Subtract')

		if event.keysym in increment_strings:
			self.increaseSize ()
		elif event.keysym in decrement_strings:
			self.decreaseSize ()
		else:
			raise ValueError, "Unknown event.keysym value for a font size event: %s" % (event.keysym)


	def run (self):
		''' Convenience wrapper to invoke all necessary
		    instance methods. Because this includes
		    :func:`Window.mainloop`, :func:`Window.run`
		    will not return until the interface is shutting down.
		'''

		self.processEventQueue ()
		self.processMonitorQueue ()

		self.mainloop ()


	def processEventQueue (self):
		''' Process any events in the event queue.
		'''

		# Process the queue until the queue is empty.
		# This could, in bizarre circumstances, starve
		# the mainloop for CPU time-- if the queue is
		# never empty, this loop never ends.

		while True:
			try:
				event = Event.get ()

			except IndexError:
				# No further pending events.
				break

			except Event.ShutdownError:
				# No further processing.
				return

			# The queue was not empty; invoke the
			# now de-queued callback.

			callback, arguments = event

			try:
				callback (*arguments)
			except:
				Log.error ("Error on Event callback:\n%s" % (traceback.format_exc ()))


		# Invoke this function again after a delay.

		self.top.after (Event.delay, self.processEventQueue)


	def processMonitorQueue (self):
		''' Process any events in the monitor queue.
		'''

		# Process the queue until the queue is empty.
		# This could, in bizarre circumstances, starve
		# the mainloop for CPU time-- if the queue is
		# never empty, this loop never ends.

		empty = False

		while True:
			try:
				keyword = Monitor.get ()

			except IndexError:
				# No further keywords requiring monitoring.
				empty = True
				break


			# Skip keyword objects that are already
			# being monitored.

			if keyword['monitored'] == True:
				continue


			# Attempt to monitor the de-queued keyword.

			try:
				keyword.monitor (wait=False)

			except ktl.ktlError:
				# Put it back on the queue. Discontinue further
				# iteration, try again after the normal delay.

				Monitor.put (keyword)
				self.setError ("One or more dispatchers appear to be offline. Once all dispatchers are running and responding to requests, this GUI will automatically make itself available for use. There is no need to close and restart this GUI.", 1000)
				break


		# If the queue is empty, clear any errors. If it is not
		# empty, invoke this function again after a delay.

		if empty == True:
			self.setError (None)
			self.processMonitorQueue.im_func.active = False
		else:
			delay = Event.delay * 10
			self.top.after (delay, self.processMonitorQueue)


	def shutdown (self):
		''' Shut down the queue of events; this effectively stops
		    all activity in the GUI module.
		'''

		Event.shutdown ()


	def initializeService (self, service, main=False):
		''' Establish a locally retained :class:`ktl.Service` instance
		    for the requested *service*. The new instance is returned
		    to the caller; it is also stored for future reference in the
		    Main.services dictionary, keyed by service name.
		'''

		Service = ktl.Service (service)
		self.services[service] = Service

		# Assume that the first service we initialize is the
		# primary service for this Main.Window instance. Setting
		# 'main' to True will explicitly assert this condition.

		if self.service == None or main == True:
			self.service = Service

		return Service


	def debug (self):
		''' Establish a log file recording debug information.
		'''

		import os
		import time

		executable = os.path.basename (sys.argv[0])

		logfile = '~/%s_log.%d' % (executable, time.time ())

		logfile = os.path.expanduser (logfile)

		self.logfile = open (logfile, 'w')

		ktl.logger (self.logfile)
		ktl.loglevel (ktl.LOG_DEBUG)

		ktl.log (ktl.LOG_INFO, "GUI: %s" % (executable))
		ktl.log (ktl.LOG_INFO, "GUI: ktl version %d" % (ktl.version ()))


	def title (self, title=None):
		''' Wrapper to the toplevel title() method.
		'''

		if title == None:
			return self.top.title ()

		return self.top.title (title)


	def mainloop (self):
		''' Wrapper to the toplevel mainloop() method.
		'''

		self.top.mainloop ()


	def checkHeartbeat (self, heartbeats=None):
		''' Watch the designated heartbeat keyword(s) for
		    activity every five seconds. 'heartbeats' is
		    expected to be an iterable object.

		    This function is only invoked via Tkinter mechanisms,
		    not via direct callbacks, and as such does not need
		    to use the Event indirect callback handling mechanism.
		'''

		initialize = False

		if heartbeats != None:

			# Initialize (or re-initialize) our notion of
			# the heartbeat keywords to match the designated
			# set of keywords.

			if len (self.heartbeats) != 0:
				self.heartbeats = {}
			if len (self.heartbeat_ok) != 0:
				self.heartbeat_ok = {}

			initialize = True



		for heartbeat in self.heartbeats.keys ():

			if heartbeat['populated'] == True:
				newbeat = heartbeat['ascii']
			else:
				newbeat = None

			if heartbeat['error'] != None or heartbeat['populated'] == False:
				self.setError ("The '%s' dispatcher heartbeat keyword '%s' can no longer be read; this generally indicates that the dispatcher associated with that keyword is no longer running. When that dispatcher is restored to service, this GUI will automatically make itself available for use. There is no need to close and restart this GUI." % (heartbeat['service'], heartbeat['name']), 50)

				if self.heartbeat_ok[heartbeat] == True:
					Log.error ("checkHeartbeat() %s unreadable" % (heartbeat.full_name))
					self.heartbeat_ok[heartbeat] = False

			elif newbeat == self.heartbeats[heartbeat]:
				self.setError ("The '%s' dispatcher heartbeat keyword '%s' is no longer updating; this generally indicates that the dispatcher associated with that keyword is hung, and needs to be restarted. When that dispatcher is restored to service, this GUI will automatically make itself available for use. There is no need to close and restart this GUI." % (heartbeat['service'], heartbeat['name']), 50)

				if self.heartbeat_ok[heartbeat] == True:
					Log.error ("checkHeartbeat() %s not updating" % (heartbeat.full_name))
					self.heartbeat_ok[heartbeat] = False

			else:
				if self.heartbeat_ok[heartbeat] == False:
					if hasattr (self, 'menu'):
						Log.alert ("Heartbeat read of %s now OK" % (heartbeat.full_name))
					else:
						Log.error ("checkHeartbeat() %s recovered" % (heartbeat.full_name))

				self.heartbeats[heartbeat] = newbeat
				self.heartbeat_ok[heartbeat] = True



		# Establish values in self.heartbeats as necessary, having
		# skipped over the above logic if we were in an initial state.

		if initialize == True:

			for heartbeat in heartbeats:

				if isinstance (heartbeat, ktl.Keyword):
					pass
				else:
					heartbeat = self.service[heartbeat]

				if heartbeat in self.heartbeats:
					raise RuntimeError, "heartbeat keyword '%s' checked multiple times" % (heartbeat['name'])


				# Invoking ktl.Service (hearbeat) will establish
				# monitoring on the heartbeat Keyword object.
				# It also enables use of the connection
				# failure/recovery features in KTL Python.

				service = self.services[heartbeat['service']]

				service.heartbeat (heartbeat)

				self.heartbeats[heartbeat] = None
				self.heartbeat_ok[heartbeat] = True



		# Build up a notion of whether everything's A-OK.

		self.heartbeats_ok = True

		heartbeats = self.heartbeat_ok.keys ()

		for heartbeat in heartbeats:
			status = self.heartbeat_ok[heartbeat]

			if status == False:
				self.heartbeats_ok = False

		if self.everything_ok == True and self.heartbeats_ok == False:

			self.everything_ok = False
			self.disconnect ()

		elif self.everything_ok  == False	and \
		     self.heartbeats_ok  == True	and \
		     self.dispatchers_ok == True:

			self.everything_ok = True
			self.connect ()
			self.setError (None)

		# Invoke this function again after 5 seconds.

		self.top.after (5000, self.checkHeartbeat)


	def setDispatcherCallback (self, keyword):
		''' Set up the ktl.Keyword <--> callback handshake for
		    dispatcher status callbacks, and establish monitoring
		    of that keyword.
		'''

		keyword.callback (self.dispatcherStatusCallback)
		Monitor.queue (keyword)


	def dispatcherStatusCallback (self, keyword):
		''' This function is intended to monitor broadcasts of
		    status keyword(s) from any dispatchers, and adjust
		    the state of the GUI accordingly.
		'''

		value = keyword['binary']

		self.dispatcher_state[keyword] = value

		self.dispatchers_ok = True

		for keyword in self.dispatcher_state.keys ():

			state = self.dispatcher_state[keyword]

			# A binary value of zero is 'ready'. Anything
			# else implies that the dispatchers are not
			# ready or willing to accept requests.

			if state != 0:
				self.dispatchers_ok = False

				# The keyword name is something like DISP1STA.
				# Snip out the number.

				dispatcher_number = keyword['name'][4:-3]

				Event.queue (Log.alert, "dispatcher #%s is unable to talk to controller #%s" % (dispatcher_number, dispatcher_number))

		if self.dispatchers_ok == False and self.everything_ok == True:

			self.everything_ok = False

			Event.queue (self.disconnect)

		elif self.everything_ok  == False and \
		     self.dispatchers_ok == True  and \
		     self.heartbeats_ok  == True:

			self.everything_ok = True

			Event.queue (self.connect)
			Event.queue (Log.alert, "All dispatcher/controller connectivity issues are now resolved.")


	def connect (self):
		''' Enable direct (non-broadcast) keyword activity.
		'''

		self.menu.connect ()

		for box in self.info_boxes:
			box.connect ()


	def disconnect (self):
		''' Disable any direct (non-broadcast) keyword activity
		    until further notice.
		'''

		self.menu.disconnect ()

		for box in self.info_boxes:
			box.disconnect ()


	def popupStructure (self, popup):
		''' Return a list of columns (as Box.Color instances) used
		    to build a Popup.Selection instance.

		    All Box.Color instances are re-gridded to row 1, as is
		    appropriate for Popup.Selection instances.
		'''

		boxes = []

		for box in self.color_boxes:
			background = box['background']

			newbox = Box.Color (popup, background=background)
			newbox.rows = []

			newbox.grid (row=1)
			boxes.append (newbox)



		def processBox (popup_box, box):
			stage = box.stage
			quartets = box.parameters ()

			# Try to use the same row alignment as the parent
			# Main.Window. Need to add one to the target row
			# because the Popup.Selection instance starts with
			# row 1, not row 0.

			target_grid = box.grid_info ()
			target_row  = int (target_grid['row']) + 1

			while popup_box.next_row < target_row:
				popup_box.rowTick ()

			for quartet in quartets:

				label, value, origin, keyword = quartet

				if label == None or len (label) == 0:

					raise RuntimeError, "Main.Window.popupStructure() received a bad quartet from an Info box: %s" % (str (quartet))

				if label[-1] != ':':
					label = '%s:' % (label)

				new_row = Popup.SelectRow (popup, popup_box, label, keyword, value, stage)
				new_row.setOrigin (origin)


		# There's a bit of indirection here. We iterate over the
		# color boxes from the main window, creating matching rows
		# in the corresponding popup box.

		for index in range (len (self.color_boxes)):

			popup_box = popup.color_boxes[index]
			color_box = self.color_boxes[index]

			# Pick out the 'white' info boxes in each 'color'
			# box, and add checkbox rows for each one.

			for info_box in color_box.boxes:

				if info_box.hidden == True:
					continue

				processBox (popup_box, info_box)


# end of class Window



class Cascade (Tkinter.Menu):

	def __init__ (self, master, main=None):

		Tkinter.Menu.__init__ (self,
					master		 = master,
					foreground	 = 'black',
					background	 = Color.menu,
					activeforeground = 'black',
					activebackground = Color.highlight,
					borderwidth	 = 2,
					font		 = Font.display,
					relief		 = 'solid',
					tearoff		 = False)


# end of class Cascade



class Menu (Cascade):

	def __init__ (self, main, actions=True):

		self.main = main

		# Establish the top-level Menu.

		Cascade.__init__ (self, main.top)
		main.top['menu'] = self


		self.lock = threading.Lock ()

		# Add our sub-menus.

		file_menu = Cascade (self)
		self.add_cascade (label='File', menu=file_menu)

		self.file_menu = file_menu

		if actions == True:
			actions_menu   = Cascade (self)
			calibrate_menu = Cascade (self)

			self.add_cascade (label='Actions', menu=actions_menu)

			self.actions_menu   = actions_menu
			self.calibrate_menu = calibrate_menu


		# A trailing spot on the Menu will be used to display
		# a message.

		self.message_index	= None
		self.message_content	= None
		self.message_expiration	= None

		if hasattr (self, 'message'):

			Log.addSiren (self.message)

		# Commands attached to the menus.

		file_menu.add_command (label='Increase font size  (Ctrl++)', command=self.main.increaseSize)
		file_menu.add_command (label='Decrease font size  (Ctrl+-)', command=self.main.decreaseSize)
		file_menu.add_separator ()
		file_menu.add_command (label='Quit (Ctrl+q)', command=self.quit)

		if actions == True:

			actions_menu.add_command (label='Cancel pending (Ctrl+c)', command=self.clearChoices)
			actions_menu.add_command (label='Apply pending (Ctrl+m)', command=self.applyChoices)
			actions_menu.add_separator ()
			actions_menu.add_command (label='Enable motion', command=self.enableMotion)
			actions_menu.add_cascade (label='Calibrate', menu=calibrate_menu)
			actions_menu.add_separator ()
			actions_menu.add_command (label='Stop all motion', command=self.stopAction)
			actions_menu.add_command (label='Lock stages...', command=self.lockAction)
			actions_menu.add_command (label='Unlock all', command=self.unlockAction)

			calibrate_menu.add_command (label='Uncalibrated stages', command=self.calibrateSelectively)
			calibrate_menu.add_command (label='All stages', command=self.calibrateAll)

		# Key-bindings for size changes.

		main.top.bind_all ('<Control-KeyPress-KP_Add>', self.main.handleResizeEvent)
		main.top.bind_all ('<Control-KeyPress-KP_Subtract>', self.main.handleResizeEvent)
		main.top.bind_all ('<Control-KeyPress-equal>', self.main.handleResizeEvent)
		main.top.bind_all ('<Control-KeyPress-plus>', self.main.handleResizeEvent)
		main.top.bind_all ('<Control-KeyPress-minus>', self.main.handleResizeEvent)

		# Bindings for basic GUI functions.

		main.top.bind_all ('<Control-KeyPress-q>', self.quit)
		main.top.bind_all ('<Control-KeyPress-Q>', self.quit)

		main.top.bind ('<Control-KeyPress-w>', self.quit)
		main.top.bind ('<Control-KeyPress-W>', self.quit)

		if actions == True:
			main.top.bind_all ('<Control-KeyPress-c>', self.clearChoices)
			main.top.bind_all ('<Control-KeyPress-C>', self.clearChoices)

			main.top.bind_all ('<Control-KeyPress-m>', self.applyChoices)
			main.top.bind_all ('<Control-KeyPress-M>', self.applyChoices)


	def quit (self, *ignored):
		''' Wrapper to Tkinter.Menu.quit(), after tossing
		    event information.
		'''

		Cascade.quit (self)


	def write (self, keyword, value, wait=False):
		''' Many menu actions want to write values to ktl.Keyword
		    objects. This method exists for convenience's sake,
		    so that these actions aren't littered with try/except
		    clauses.
		'''

		try:
			keyword.write (value, wait)
		except:
			Log.alert ("Unable to write '%s' to %s" % (value, keyword['name']))
			ktl.log (ktl.LOG_ERROR, "GUI.Main.Menu.write(): Error writing '%s' to %s:\n%s" % (value, self.keyword['name'], traceback.format_exc ()))


	def stopAction (self, *ignored):

		Stage.stopAll (self.main.service)


	def lockAction (self, *ignored):

		dialog_popup = Popup.Lock (self.main)


	def unlockAction (self, *ignored):

		for box in self.main.info_boxes:
			lock = '%sLCK' % (box.stage)

			for service in self.main.services.values ():

				if lock in service:
					keyword = self.main.service[lock]

					if keyword['populated'] and \
					   keyword['monitored'] == True:

						value = keyword['ascii']
					else:
						value = keyword.read ()

					value = value.lower ()

					# The empty string and 'unlocked' both
					# represent the unlocked state, though
					# the label on the detail panel will
					# indicate 'Unlocked' when the LCK
					# keyword is the empty string.

					if value != '' and value != 'unlocked':
						self.write (keyword, '')


	def enableMotion (self, *ignored):
		''' Prepare each identified standard stage for motion.
		    In the most basic case, that means setting their
		    control modes to 'Pos'.
		'''

		services = self.main.services.values ()

		for stage in Stage.stages:

			mode = '%sMOD' % (stage)
			keyword = None

			for service in services:
				if mode in service:
					keyword = service[mode]

			if keyword == None:
				# No %MOD keyword for this stage.
				continue

			if keyword['monitored'] == True:
				mode = keyword['ascii']
			else:
				mode = keyword.read (wait=True)

			# Only look at the first three characters of the mode,
			# since it could be 'pos on' or 'pos off', not just
			# 'pos'.

			mode = mode[:3].lower ()

			if mode != 'pos':
				self.write (keyword, 'pos')


	def calibrateSelectively (self, *ignored):

		self.calibrateAction (force=False)


	def calibrateAll (self, *ignored):

		self.calibrateAction (force=True)


	def calibrateAction (self, force):

		if self.main.everything_ok:
			pass
		else:
			Log.alert ('NOT calibrating any stages, no connection to dispatcher(s).')
			return

		if force == True:
			Log.alert ('Recalibrating all stages...')
		else:
			Log.alert ('Calibrating uncalibrated stages...')

		Event.queue (Stage.calibrateAll, self.main.service, force)


	def clearChoices (self, *ignored):

		for box in self.main.info_boxes:

			try:
				if box.value.choice != None:
					box.value.choose (None)
			except AttributeError:
				pass


	def applyChoices (self, *ignored):

		if self.main.everything_ok == False:
			Log.alert ('NOT writing, do not have connection to dispatcher(s).')
			return None

		for box in self.main.info_boxes:

			try:
				value  = box.value
				choice = value.choice
				valid  = value.valid
				write  = value.write
			except AttributeError:
				continue

			if choice == None or valid == False:
				continue

			if callable (write):
				write ()


	def message (self, text=None, delay=5):
		''' Display the given text, if any, on the Menu.
		    If text == None, any message currently displayed
		    will be cleared immediately.

		    Messages expire after five seconds. This can be
		    changed by setting the 'delay' argument to some
		    other value. If 'delay' is set to None, the message
		    will not expire until it is overwritten.
		'''

		self.lock.acquire ()

		if self.message_content != None:

			self.delete (self.message_index)

			self.message_index   = None
			self.message_content = None

		if text != None:

			self.message_content = text

			# Prepend whitespace on the text. It needs to be
			# spaces instead of a tab, as the tab character
			# gets rendered as '\t' on the menu bar.

			prefix = 8 * ' '
			text = text.strip ()
			text = prefix + text

			# 'command' must be specified, or else Tkinter will
			# not be able to delete the message later on.

			self.add_command (label=text, state=Tkinter.DISABLED, command=self.message)

			self.message_index = self.index (Tkinter.END)


		# Cancel any previously-existing message clearing event.

		if self.message_expiration != None:

			self.after_cancel (self.message_expiration)
			self.message_expiration = None

		# If a message was set, establish a message-clearing event.

		if text != None and delay != None:

			# The delay argument is in seconds, but Tkinter's
			# after() method works in milliseconds.

			delay = delay * 1000

			self.message_expiration = self.after (delay, self.message)

		self.lock.release ()


	def connect (self):
		''' Enable direct (non-broadcast) keyword activity.
		'''

		last = self.index (Tkinter.END)

		index = 0
		while index <= last:

			try:
				label = self.entrycget (index, 'label')
			except:
				index += 1
				continue

			if label == 'Actions':

				state = self.entrycget (index, 'state')

				if state != Tkinter.NORMAL:
					self.entryconfigure (index, state=Tkinter.NORMAL)

			index += 1


	def disconnect (self):
		''' Disable any direct (non-broadcast) keyword activity
		    until further notice.
		'''

		last = self.index (Tkinter.END)

		index = 0
		while index <= last:

			try:
				label = self.entrycget (index, 'label')
			except:
				index += 1
				continue

			if label == 'Actions':

				state = self.entrycget (index, 'state')

				if state != Tkinter.DISABLED:
					self.entryconfigure (index, state=Tkinter.DISABLED)

			index += 1


# end of class Menu
