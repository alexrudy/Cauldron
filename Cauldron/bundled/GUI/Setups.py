import version
version.append ('$Revision: 89494 $')
del version


import ktl
import os
import time
import tkFileDialog
import Tkinter
from Tkinter import N, E, S, W
import traceback

import Color
import Font
import Event
import Log
import Popup as kPopup		# avoid name conflict with class Popup below
import Value


description = None
directory = '~/observers'
extension = None
mode = 0744
preamble = None
prefix = ''


def setDirectory (path):

	if os.path.isabs (path):
		pass
	else:
		path = os.path.expanduser (path)

	if os.path.isdir (path):
		pass
	else:
		raise ValueError, "directory does not exist: %s" % (path)

	global directory
	directory = path


try:
	setDirectory (directory)
except ValueError:
	directory = None



def setDescription (string):

	global description
	description = string



def setExtension (string):

	global extension
	extension = string



def setPreamble (string):

	global preamble
	preamble = string



def setPrefix (string):

	global prefix
	prefix = string



def shortname (filename):
	''' Return the base setup filename with no extension.
	    If an absolute path is provided, the directory
	    components will be removed.
	'''

	extension_length = len (extension)

	filename  = os.path.basename (filename)
	shortname = filename[:-extension_length]

	return shortname



class Bar:

	def __init__ (self, main):

		frame = Tkinter.Frame (master		= main.top,
					background	= Color.menu,
					borderwidth	= 0,
					relief		= 'solid')

		menu  = Menu (master=frame, main=main)
		label = Value.WhiteLabel (master=frame, text='Instrument setups')

		self.main  = main
		self.menu  = menu
		self.frame = frame
		self.label = label

		self.grid = frame.grid
		self.grid_remove = frame.grid_remove

		frame.columnconfigure (0, weight=0)
		frame.columnconfigure (1, weight=1)
		frame.rowconfigure    (0, weight=0)

		label.grid (row=0, column=0, padx=(7,0), pady=3, sticky=W)
		menu.grid  (row=0, column=1, padx=3, sticky=W)


		# Need to shift the frames about in the Main.Window.

		main.frame.grid (row=1)
		self.frame.grid (row=0, column=0, sticky=N+E+S+W)

		main.top.rowconfigure (0, weight=0)
		main.top.rowconfigure (1, weight=1)


# end of class Bar



class Setup:
	''' This is a helper class to encapsulate the logic asserting
	    whether or not a given setup matches the active state of
	    the instrument. Almost as a side effect, it retains the
	    original content of the setup, and can distribute its
	    choices to the Main.Window.
	'''

	numeric = {'KTL_DOUBLE': True, 'KTL_FLOAT': True, 'KTL_INT': True}

	def __init__ (self, filename, main, watch=True):

		self.main     = main
		self.filename = filename

		self.choices = {}
		self.watching = {}

		self.loadSetup ()

		if watch == True:
			self.watch ()


	def match (self):
		''' Return True if the current available state matches
		    the saved setup.
		'''

		if len (self.watching) == 0:
			raise RuntimeError, "can't match() a setup without first invoking watch()"

		for keyword in self.keywords ():
			if keyword['populated'] == False:
				return False

			new    = keyword['ascii']
			target = self.watching[keyword]

			if keyword['type'] in self.numeric:
				new = float (new)

				if keyword['type'] == 'KTL_INT':
					new = int (new)
			else:
				new = new.lower ()

			if new != target:
				return False

		return True


	def keywords (self):
		''' Provide a tuple containing all the keywords of interest
		    to this Setup.
		'''

		return self.watching.keys ()


	def loadSetup (self):

		if self.filename == None:
			return

		prefix_length = len (prefix)


		setup = open (self.filename, 'r')
		contents = setup.read ()
		setup.close ()

		lines = contents.split ('\n')


		for line in lines:

			if line[:prefix_length] == prefix:

				choice = {}

				components = line.split ()

				keyword	= components[1]

				# If a keyword choice includes embedded
				# whitespace, it got butchered with the
				# line.split () above.

				if len (components) > 3:
					# Remove leading prefix.
					choice = line[prefix_length:]
					choice = choice.strip ()

					# Remove leading keyword name, which
					# may include the service name.
					choice = choice[len (keyword):]
					choice = choice.strip ()
				else:
					# No embedded whitespace.
					choice = components[2]


				# New setup files have the service
				# name embedded in the 'keyword' field,
				# in the form 'service.KEYWORD'. Old files
				# only specify the keyword.

				service = None

				if '.' in keyword:

					service,keyword = keyword.split ('.', 1)

					service = service.strip ()
					keyword = keyword.strip ()

					if service == '' or keyword == '':
						# Badly formed pair. Assume
						# it is just a keyword.

						service = None
						keyword = components[1]

				# If no service is specified, it is
				# implied that the main.service is
				# appropriate.

				if service == None:

					service = self.main.service.name


				if service in self.choices:
					pass
				else:
					self.choices[service] = {}

				self.choices[service][keyword] = choice


	def watch (self, expand=True):
		''' Ensure that all Keyword objects associated with this
		    setup are being monitored. We don't need to register
		    any callbacks, because state is only inspected when
		    self.match () is invoked.

		    If expand is set to True, and if the SWT keyword exists
		    for the relevant stage (if any), monitoring of RAW will
		    be replaced by TRG, VAL by TVA, and VAX by TVX.
		'''

		services = self.main.services

		for service in self.choices.keys ():

			if service in services:
				pass
			else:
				ktl.log (ktl.LOG_INFO, "GUI: unknown service '%s' used in setup '%s'" % (service, self.filename))
				continue

			for keyword in self.choices[service].keys ():

				if expand == True:

					# Swap out the 'actual' keyword for the
					# 'target', and add in monitoring of
					# the 'sweet' keyword that indicates
					# whether the actual value is still
					# within tolerance of the target.
					# If either keyword does not exist,
					# fall back to using the original
					# keyword.

					prefix = keyword[:-3]
					suffix = keyword[-3:]

					sweet = '%sSWT' % (prefix)

					if sweet in services[service]:

						if suffix == 'RAW':
							new = "%s%s" % (prefix, 'TRG')

						elif suffix == 'VAL':
							new = "%s%s" % (prefix, 'TVA')

						elif suffix == 'VAX':
							new = "%s%s" % (prefix, 'TVX')

						else:
							new = None

						if new != None:
							# If the 'new' keyword
							# exists, use it instead
							# of the original.

							if new in services[service]:
								self.choices[service][new] = self.choices[service][keyword]
								keyword = new
							else:
								new = None

						if new != None:
							# We're using the new
							# keyword name. Append
							# the 'sweet' keyword
							# to the set of keywords
							# being watched. String
							# matches are lower
							# case.

							sweet = services[service][sweet]

							self.watching[sweet] = 'true'

							if sweet['monitored'] == False:
								sweet.monitor (wait=False)

				if keyword in services[service]:
					choice = self.choices[service][keyword]
					keyword = services[service][keyword]
				else:
					ktl.log (ktl.LOG_INFO, "GUI: unknown keyword '%s' used in setup '%s'" % (keyword, self.filename))
					continue


				target = choice

				if keyword['type'] in self.numeric:
					target = float (target)

					if keyword['type'] == 'KTL_INT':
						target = int (target)
				else:
					target = target.lower ()

				self.watching[keyword] = target

				if keyword['monitored'] == False:
					keyword.monitor (wait=False)


	def apply (self):
		''' Iterate through all Info boxes in the Main.Window, and
		    apply the saved values as 'choices' for any Info box
		    that matches the designated keyword. It is not expected,
		    but also not assumed otherwise, that a saved value is
		    relevant for more than one Info box.
		'''

		for box in self.main.info_boxes:

			# Skip hidden boxes.

			if box.hidden == True:
				continue

			if hasattr (box, 'value'):

				value = box.value

				if hasattr (value, 'keywords'):
					keywords = value.keywords ()
				else:
					keywords = ()

				for keyword in keywords:
					service = keyword['service']
					keyword = keyword['name']

					try:
						choice = self.choices[service][keyword]
					except KeyError:
						continue

					value.choose (choice)


# end of class Setup



class Menu (Value.ArbitraryMenu):
	''' Menu object used with instrument setups. The 'active' setup,
	    if any, will be the displayed value; available setup choices for
	    a specific setups directory will be displayed in the menu cascade.

	    One menu choice at the end will be to select a new setups
	    directory. The act of choosing a new directory will cause the menu
	    to repopulate.
	'''

	def __init__ (self, *args, **kwargs):

		kwargs['go'] = False
		Value.ArbitraryMenu.__init__ (self, *args, **kwargs)

		self.directory_timestamp = None
		self.file_timestamps = None

		self.check_delay = Event.delay * 20
		self.directory_check = None
		self.file_check = None
		self.clear_at_noon = None

		self.directory	= None
		self.filenames	= ()
		self.fullpaths	= ()
		self.shortnames = ()

		self.setups = {}
		self.matches = {}
		self.watching = {}

		self.last_choice = None

		self.buildMenu (())
		self.redraw ()


	def choose (self, choice):
		''' A 'choice' for a Menu is an instrument setup.
		    For the chosen setup, apply its individual settings
		    to the rest of the GUI.
		'''

		# Main.Window.clearChoices() will invoke choose (None).
		# Don't do anything with it, because we never have a
		# choice set, we only use overrides.

		if choice == None:
			return

		self.setups[choice].apply ()

		if self.last_choice != choice:

			self.last_choice = choice
			Event.queue (self.redraw)


	def receiveCallback (self, keyword):
		''' Check any known setups for interest in this keyword.
		    If there are any, check for matches.
		'''

		if keyword in self.watching:
			setups = self.watching[keyword]
		else:
			# Shouldn't happen. We should only get callbacks
			# for keywords that have watchers associated with
			# them.
			return

		changed = False

		for setup in setups:

			match = setup.match ()

			if match == False and setup in self.matches:
				del self.matches[setup]
				changed = True

			elif match == True:
				if setup in self.matches:
					pass
				else:
					short = shortname (setup.filename)
					self.matches[setup] = short
					changed = True

			if changed == True:
				Event.queue (self.redraw)


	def setMenu (self, menu_items):
		''' Add options to the end of the menu to manipulate
		    the displayed list of setups.
		'''

		# Putting an empty tuple in the list indicates the desire
		# for a menu separator.

		menu_items.append (())

		if self.directory != None:
			label = 'Clear setup list'
			command = self.forgetDirectory

			menu_items.append ((label, command))


			label = 'Load new setup file...'
			command = self.chooseFile

			menu_items.append ((label, command))


			# Different label for the next menu item.
			label = 'Choose new directory...'

		else:
			label = 'Load setup file...'
			command = self.chooseFile

			menu_items.append ((label, command))

			# Different label for the next menu item.
			label = 'Choose directory...'

		command = self.chooseDirectory

		menu_items.append ((label, command))


		label = 'Save new setup...'
		command = self.saveSetup

		menu_items.append ((label, command))

		return Value.ArbitraryMenu.setMenu (self, menu_items)


	def redraw (self):

		override = None

		# Determine just how much room we have, in characters.

		width = self.master.winfo_width ()
		size  = Font.display.cget ('size')

		characters = int (width / size)

		# Lop off an arbitrary number of characters to allow
		# for a label on the left side.

		characters = characters - 20


		# Track which setups are already in the displayed value,
		# since we might approach them out of order later on.

		included = []

		if self.last_choice != None and self.last_choice in self.setups:

			setup = self.setups[self.last_choice]

			if setup in self.matches:
				override = self.last_choice
				included.append (self.last_choice)


		if override == None and len (self.matches) != 0:

			# Since the user's last chosen setup is not
			# currently a match, grab any old match and
			# display it.

			matches = self.matches.values ()
			matches.sort ()
			override = matches[0]

			included.append (matches[0])


		if override != None and len (self.matches) > 1:

			# Show more than one name if we have enough
			# space. Leave enough room for the '+# more'.

			maximum = characters - 7
			displayed = 1

			for name in self.matches.values ():

				if len (override) >= maximum:
					break

				if name in included:
					continue

				if len (override) + len (name) + 2 > maximum:
					continue

				override = "%s, %s" % (override, name)
				included.append (name)
				displayed += 1

			remainder = len (self.matches) - displayed

			if remainder > 0:
				remainder = "+%d more" % (remainder)

				if len (included) > 1:
					override = "%s, %s" % (override, remainder)
				else:
					override = "%s %s" % (override, remainder)


		if override == None:
			self.setOverride ('None')
		else:
			self.setOverride (override)

		# Having determined what the displayed value should
		# be, redraw.

		Value.ArbitraryMenu.redraw (self)

		# Now that the menu is guaranteed to be fully established,
		# highlight the matching setup(s) in the menu. If there are
		# no matches, ensure that nothing is highlighted.

		matches = self.matches.values ()

		index = 0

		while True:
			try:
				label = self.menu.entrycget (index, 'label')
			except:
				# Tried to get the label on a separator.
				# There is only one separator in this menu,
				# and there are no setups listed beyond it.
				break

			background = self.menu.entrycget (index, 'background')

			if label in matches:
				if background != Color.selection:
					self.menu.entryconfigure (index, background=Color.selection)
			elif background != Color.white:
				self.menu.entryconfigure (index, background=Color.white)

			index += 1


	def setDirectory (self, directory):

		if directory == self.directory:
			return False

		# Initialize our contents for this new directory.

		self.directory_timestamp = None
		self.directory = directory
		self.last_choice = None

		self.checkDirectory ()

		# If it is after noon local time, or before 6AM, set a
		# timed event to clear the list of displayed setups
		# at noon.

		if self.clear_at_noon == False:
			# Do no clearing.
			pass

		elif directory != None:
			now  = time.localtime ()
			hour = now.tm_hour

			if hour < 6 or hour >= 12:

				hours = 12 - hour

				if hour >= 12:
					hours = hours + 24

				# Add an extra minute to the timer to ensure
				# that the expiration happens after the clock
				# strikes 12.

				minutes = hours * 60 - now.tm_min + 1

				seconds = minutes * 60

				milliseconds = seconds * 1000

				self.clear_at_noon = self.after (milliseconds, self.forgetDirectory)

		elif self.clear_at_noon != None:
			# No directory active, there isn't anything to clear.
			self.after_cancel (self.clear_at_noon)
			self.clear_at_noon = None

		return True


	def forgetDirectory (self, *ignored):
		''' Establish a clean slate for the menu.
		'''

		self.setDirectory (None)
		self.clearSetups ()
		self.last_choice = None
		Event.queue (self.redraw)


	def checkDirectory (self):
		''' Check the timestamp on the directory. If it has
		    changed, reload the file list.
		'''

		if self.directory == None:

			self.directory_timestamp = None

			if self.directory_check != None:
				self.after_cancel (self.directory_check)
				self.directory_check = None

			if self.file_check != None:
				self.after_cancel (self.file_check)
				self.file_check = None

			return


		times = os.stat (self.directory)
		mtime = times.st_mtime

		if mtime != self.directory_timestamp:
			self.directory_timestamp = mtime
			self.loadDirectory ()

			# loadDirectory () cleared the menu. Put it back.

			self.buildMenu (self.shortnames)

			self.checkFiles ()

			# Check for matches.

			for keyword in self.watching.keys ():
				self.receiveCallback (keyword)

			# If there weren't any matches, we need to redraw the
			# menu to initialize its display.

			if len (self.matches) == 0:
				Event.queue (self.redraw)


		if self.directory_check != None:
			self.after_cancel (self.directory_check)

		self.directory_check = self.after (self.check_delay, self.checkDirectory)


	def loadDirectory (self):

		self.clearSetups ()

		if self.directory == None:
			return

		files = os.listdir (self.directory)
		files.sort ()

		self.file_timestamps = {}

		filenames = []
		fullpaths = []
		shortnames = []

		tag = extension
		tag_length = len (extension)

		for file in files:

			# Skip non-setup files.

			if file[-tag_length:] != tag:
				continue

			fullpath  = os.path.join (self.directory, file)
			short = shortname (file)

			filenames.append (file)
			fullpaths.append (fullpath)
			shortnames.append (short)

		self.filenames	= filenames
		self.fullpaths	= fullpaths
		self.shortnames = shortnames

		if len (shortnames) == 0:
			self.forgetDirectory ()


	def checkFiles (self):
		''' Check the known timestamp for all the setup files we're
		    tracking, and stat the file to look for any changes.
		    In the event that there are changes, reload the setup
		    file.
		'''

		if self.directory == None:
			if self.file_check != None:
				self.after_cancel (self.file_check)
				self.file_check = None

			return

		redraw = False

		for file in self.fullpaths:

			try:
				times = os.stat (file)

			except OSError:
				# File is gone. This will get handled by
				# checkDirectory() since the directory
				# mtime changed.

				continue

			mtime = times.st_mtime

			if file in self.file_timestamps:

				if mtime != self.file_timestamps[file]:

					try:
						self.loadSetup (file)
					except:
						self.invalidSetup (fullpath=file)
						Log.error ("Error loading '%s':\n%s" % (file, traceback.format_exc ()))
						continue

					redraw = True

			else:
				try:
					self.loadSetup (file)
				except:
					self.invalidSetup (fullpath=file)
					Log.error ("Error loading '%s':\n%s" % (file, traceback.format_exc ()))
					continue

				redraw = True

		if redraw == True:
			Event.queue (self.redraw)

		if self.file_check != None:
			self.after_cancel (self.file_check)

		self.file_check = self.after (self.check_delay, self.checkFiles)


	def invalidSetup (self, filename=None, fullpath=None, shortname=None):
		''' Remove a specific setup from the menu. This is only
		    invoked by self.checkFiles() in the event that
		    a setup file does not successfully load.
		'''

		if filename != None:
			index = self.filenames.index (filename)
		elif fullpath != None:
			index = self.fullpaths.index (fullpath)
		elif shortname != None:
			index = self.shortnames.index (shortname)
		else:
			raise RuntimeError, 'cannot invoke invalidSetup() with no arguments'

		filename = self.filenames[index]

		Log.alert ("Invalid setup file: %s" % (filename))

		self.filenames.pop (index)
		self.fullpaths.pop (index)
		self.shortnames.pop (index)

		self.buildMenu (self.shortnames)
		self.redraw ()


	def clearSetups (self):
		''' Remove all known setups, and clean up any lingering
		    callbacks.
		'''

		if self.directory_check != None:
			self.after_cancel (self.directory_check)
			self.directory_check = None

		if self.file_check != None:
			self.after_cancel (self.file_check)
			self.file_check = None

		self.matches   = {}
		self.filenames = ()
		self.fullpaths = ()

		for shortname in self.shortnames:

			setup = self.setups[shortname]
			del (self.setups[shortname])

		self.shortnames = ()


		for keyword in self.watching.keys ():

			keyword.callback (self.receiveCallback, remove=True)
			del (self.watching[keyword])

		# Having tidied up everything else, build and empty menu.
		self.buildMenu (())


	def chooseDirectory (self, *ignored):

		if description == None:
			raise RuntimeError, 'Setups.description must be defined in order to work with setups'

		if self.directory == None:
			# Use the module default.
			initial = directory
		else:
			initial = self.directory

		name = tkFileDialog.askdirectory (title='Select a directory containing %s' % (description),
						initialdir=initial,
						mustexist=True)

		# And, the results...

		if name == None or name == () or name == '':
			# No directory chosen, maybe they hit cancel. That's OK.
			return

		changed = self.setDirectory (name)


	def chooseFile (self, *ignored):

		if description == None:
			raise RuntimeError, 'Setups.description must be defined in order to work with setups'

		if extension == None:
			raise RuntimeError, 'Setups.extension must be defined in order to work with setups'

		if prefix == None:
			raise RuntimeError, 'Setups.prefix must be defined in order to work with setups'

		if self.directory == None:
			initial = directory
		else:
			initial = self.directory

		filename = tkFileDialog.askopenfilename (title='Select a %s file' % (extension),
						defaultextension=extension,
						initialdir=initial,
						filetypes=[(description, extension), ('all', '.*')],
						multiple=False)

		# And, the results...

		if filename == None or filename == () or filename == '':
			# No file chosen, maybe they hit cancel. That's OK.
			return

		basedir = os.path.dirname (filename)
		changed	= self.setDirectory (basedir)
		redraw	= False

		short = shortname (filename)

		if self.last_choice != short:
			self.last_choice = short
			redraw = True


		if changed == False and redraw == True:

			# Same directory, but the user selected a different
			# file as their choice. Update the display.

			Event.queue (self.redraw)


		if self.last_choice != None:
			self.setups[self.last_choice].apply ()


	def saveSetup (self, *ignored):

		Popup (self.main)


	def loadSetup (self, file):

		times = os.stat (file)
		mtime = times.st_mtime
		short = shortname (file)

		if short in self.setups:

			old = self.setups[short]

			try:
				del (self.matches[old])
			except KeyError:
				pass

			for keyword in self.watching.keys ():
				if old in self.watching[keyword]:
					self.watching[keyword].remove (old)


		self.file_timestamps[file] = mtime

		setup = Setup (file, self.main)
		self.setups[short] = setup

		keywords = setup.keywords ()

		for keyword in keywords:

			if keyword in self.watching:
				pass
			else:
				self.watching[keyword] = []
				keyword.callback (self.receiveCallback)

			self.watching[keyword].append (setup)

			# Check for matches.
			self.receiveCallback (keyword)

# end of class Menu



class Popup (kPopup.Selection):

	def __init__ (self, main):

		kPopup.Selection.__init__ (self, main)

		self.top.title ('Select values for saved setup')

		self.frame.rowconfigure (0, weight=0)


		self.action_button['text'] = 'Save as...'
		self.action_button['command'] = self.save

		self.checkButtons ()


		# Go back through the set of discovered keyword values,
		# and do intelligent substitution of RAW/VAL/VAX for
		# their respective 'target' keyword, TRG/TVA/TVX.

		for row in self.rows:

			# Skip rows whose value was set via an active
			# choice, which is already effectively a target
			# value.

			if row.origin == 'choice':
				continue

			keyword = row.keyword

			if isinstance (keyword, ktl.Keyword):
				pass
			else:
				continue

			suffix = keyword['name'][-3:]

			if suffix == 'RAW' or suffix == 'VAL' or suffix == 'VAX':

				prefix	= keyword['name'][:-3]
				service = keyword['service']
				service = self.main.services[service]

				if suffix == 'RAW':
					target = 'TRG'
				elif suffix == 'VAL':
					target = 'TVA'
				elif suffix == 'VAX':
					target = 'TVX'

				target = "%s%s" % (prefix, target)
				sweet  = "%s%s" % (prefix, 'SWT')

				if target in service and sweet in service:

					sweet = service[sweet]

					if sweet['populated'] == True and \
					   sweet['monitored'] == True:

						sweet = sweet['binary']
					else:
						sweet = sweet.read (binary=True)

					if sweet == False:
						# Not in tolerance. Don't store
						# the target value, store the
						# actual value. Go to the next
						# SelectRow.

						continue

				else:
					# No keyword to indicate that the stage
					# is still within tolerance, or no
					# target keyword exists. Either way,
					# skip ahead to the next SelectRow.

					continue

				# Replace the 'actual' value with the 'target'
				# value.

				target = service[target]

				if target['populated'] == True and \
				   target['monitored'] == True:

					target = target['ascii']
				else:
					target = target.read ()

				row.value = target

				Event.tkSet (row.choice, 'text', target)


	def save (self):

		if description == None:
			raise RuntimeError, 'Setups.description must be defined in order to work with setups'

		if extension == None:
			raise RuntimeError, 'Setups.extension must be defined in order to work with setups'

		if preamble == None:
			raise RuntimeError, 'Setups.preamble must be defined in order to work with setups'

		# Toss up a file chooser.

		filename = tkFileDialog.asksaveasfilename (title='Save as...',
						defaultextension=extension,
						initialdir=directory,
						initialfile='new_setup%s' % (extension),
						filetypes=[(description, extension), ('all', '.*')])

		# And, the results...

		if filename == None or filename == () or filename == '':
			# No file chosen-- maybe they hit cancel. That's OK.
			pass
		else:
			# Enforce a filename suffix matching the
			# Setups.extension. The use of 'defaultextension'
			# above in asksaveasfilename() will append the correct
			# extension if *no* extension is present in the chosen
			# filename (such as 'foo'), but it will not append the
			# value if any *other* extension is present (such as
			# foo.bar).

			extension_length = len (extension)

			if len (filename) < extension_length or \
			   filename[-extension_length:] != extension:

				filename = '%s%s' % (filename, extension)

			try:
				new_file = open (filename, 'w')

			except IOError:
				# Override permissions, if possible. This
				# only occurs if the file exists, and the
				# running user can't write to it-- note
				# that in these circumstances, the user
				# was already prompted to confirm that
				# they want to overwrite the existing file.

				os.chmod (filename, 0700)

				new_file = open (filename, 'w')

			new_file.write (preamble)
			new_file.write ('\n')

			# Acquire a list of active values-- rows that
			# were actively selected, whose keyword affiliations
			# are known, and that have a value present.

			choices = []
			counts = {}

			for row in self.rows:

				if row.selected == True	and \
				   row.keyword != None	and \
				   row.value != None:

					pair = (row.keyword, row.value)
					choices.append (pair)

					try:
						counts[row.keyword] += 1
					except KeyError:
						counts[row.keyword] = 1


			# First, add in the comment-formatted values.

			for pair in choices:
				keyword = pair[0]
				value   = pair[1]
				line = '%s %s.%s %s\n' % (prefix, keyword['service'], keyword['name'], value)

				new_file.write (line)

			new_file.write ('\n')

			# Second, add in the script-formatted values.
			# Each command is a backgrounded KTL_WAIT write.
			# If there are duplicate keywords, it is essential
			# that the 'first' write finish before the 'second'
			# request is fired off.

			for pair in choices:
				keyword = pair[0]
				value   = pair[1]

				if counts[keyword] == 1:
					line = "modify -s %s %s='%s' &\n" % (keyword['service'], keyword['name'], value)
				else:
					line = "modify -s %s %s='%s'\n" % (keyword['service'], keyword['name'], value)
					counts[keyword] -= 1

				new_file.write (line)

			# Wait for the backgrounded modify's to finish,
			# regardless of success or failure, before
			# exiting the script.

			comment = '\n# Wait for all backgrounded modify calls to complete before exiting.\n'
			line = 'wait\n'

			new_file.write (comment)
			new_file.write (line)

			new_file.close ()

			os.chmod (filename, mode)

			self.destroy ()


	def checkButtons (self, box=None):
		''' In addition to the per-color selections, adjust the
		    Save As... button according to any selections.
		'''

		kPopup.Selection.checkButtons (self, box)

		# Disable the 'Save As...' button if no stages are selected.

		try:
			button = self.action_button
		except AttributeError:
			# The action button doesn't exist yet. It's possible
			# that the caller invoked toggle() while initializing
			# a popup.
			return

		if self.noneSelected ():
			Event.tkSet (button, 'state', Tkinter.DISABLED)
			Event.tkSet (button, 'cursor', '')
		else:
			Event.tkSet (button, 'state', Tkinter.NORMAL)
			Event.tkSet (button, 'cursor', 'hand2')


# end of class Popup
