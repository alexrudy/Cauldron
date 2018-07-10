from . import version
version.append ('$Revision: 1.1 $')
del version


import weakref


class WeakRef:
	''' A faithful implementation of weak references that works
	    not only for static functions and objects, but also
	    bound methods of instances. Bound methods are not handled
	    gracefully by the :mod:`weakref` module.
	'''

	def __init__ (self, thing):

		# If 'thing' is an instance method, it will have
		# both an im_func and an im_self attribute. If it
		# does not have those attributes, it is a simple
		# object, to which we can retain a direct weak
		# reference.

		try:
			self.method = weakref.ref (thing.im_func)
			self.instance = weakref.ref (thing.im_self)
			self.reference = None

		except AttributeError:
			self.reference = weakref.ref (thing)


	def __call__ (self):

		# If the 'thing' referred to is a simple object,
		# self.reference will refer to it. Return the
		# direct result of the weak reference lookup.

		if self.reference != None:
			return self.reference ()


		# Otherwise, this WeakRef instance refers to an
		# instance method. If the instance was deallocated,
		# there is no longer an instance method to refer to.

		instance = self.instance ()

		if instance == None:
			return None


		# The instance has not been deallocated; therefore,
		# it is still valid to refer to the instance method.
		# Return a new reference to the instance method;
		# a strong reference would have kept the instance
		# itself from being deallocated, and a weak reference
		# to an instance method is dead on arrival.

		method = self.method ()

		return getattr (instance, method.__name__)


# end of class WeakRef
