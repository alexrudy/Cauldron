import version
version.append ('$Revision: 84106 $')
del version


import Tkinter

import Button
import Event
import Images
import kImage


class Simple (Button.Simple):
	''' Just an image icon, without Button-ish functionality.
	'''

	def __init__ (self, master, main, background='#ffffff'):

		Button.Simple.__init__ (self, master=master, main=main, background=background)

		Event.tkSet (self, 'borderwidth', 0)
		Event.tkSet (self, 'activebackground', background)
		Event.tkSet (self, 'cursor', '')
		Event.tkSet (self, 'highlightthickness', 0)
		Event.tkSet (self, 'relief', Tkinter.SUNKEN)


	def createHighlight (*ignored):
		return

	def removeHighlight (*ignored):
		return

	def connect (*ignored):
		return

	def disconnect (*ignored):
		return

# end of class Simple



class Status (Simple):

	def __init__ (self, *arguments, **keyword_arguments):

		Simple.__init__ (self, *arguments, **keyword_arguments)

		self.motor_hold = None
		self.image_pil = kImage.Status (size=self.icon_size)
		self.setImage (Images.get ('unknown'))


	def setMotorHold (self, hold):

		# Don't try to catch exceptions about setMotorHold ()
		# not being present; its absence here is indicative of
		# a programming error.

		changed = self.image_pil.setMotorHold (hold)

		if changed == True:
			self.motor_hold = hold

		return changed


	def update (self, keyword=None, slice=None):

		new = False

		if keyword != None:
			new = self.image_pil.interpret (keyword, slice)

		changed = self.interpret (keyword, slice)

		if new == True or changed == True:
			self.redraw ()


# end of class Status
