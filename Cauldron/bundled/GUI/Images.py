import version
version.append ('$Revision: 91660 $')
del version

try:
	import Image

except ImportError:
	import PIL.Image as Image

import os


library = None


def initialize (path):

	global library
	library = Library (path)


def get (image):

	return library[image]


def set (image, filename):

	library[image] = filename


class Library:
	''' Provide a just-in-time mechanism for loading of images,
	    so that GUIs using fewer images do not need to carry
	    around unused objects in resident memory.
	'''

	def __init__ (self, path):

		if os.path.exists (path):
			pass
		else:
			raise ValueError, "base directory not found: %s" % (path)

		self.directory = path

		self.filenames = {}
		self.images = {}

		self.initialize ()


	def __getitem__ (self, image):

		image = image.lower ()
		filename = self.filenames[image]

		try:
			image = self.images[filename]
		except KeyError:
			image = self.open (image, filename)

		return image


	def __setitem__ (self, image, filename):

		if os.path.isabs (filename):
			pass
		else:
			filename = os.path.join (self.directory, filename)

		if os.path.exists (filename):
			pass
		else:
			raise ValueError, "file does not exist: %s" % (filename)

		image = image.lower ()

		try:
			del (self.images[image])
		except KeyError:
			pass

		self.filenames[image] = filename


	def open (self, name, filename):

		image = Image.open (filename)
		self.images[name] = image

		return image


	def initialize (self):

		self['ok'] = 'ok.png'
		self['warning'] = 'warning.png'
		self['cant_proceed'] = 'cant_proceed.png'
		self['error'] = 'error.png'
		self['unknown'] = 'unknown.png'

		self['locked'] = 'locked.png'
		self['maintenance'] = 'gears.png'

		self['apply'] = 'apply.png'
		self['checked'] = 'checked.png'
		self['up'] = 'up.png'
		self['down'] = 'down.png'
		self['refresh'] = 'refresh.png'

		self['forward_small'] = 'forward-small.png'
		self['forward_large'] = 'forward-large.png'
		self['reverse_small'] = 'reverse-small.png'
		self['reverse_large'] = 'reverse-large.png'

		self['bulb_on'] = 'bulb-on.png'
		self['bulb_off'] = 'bulb-off.png'

		self['path_allow'] = 'path-arrow.png'
		self['path_block'] = 'path-arrow-stop.png'

# end of class Library
