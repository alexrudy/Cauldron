
__all__ = ('version')

# Component files in the module will append their CVS $Revision string to
# the versions list. 

versions = []

append = versions.append
append ('$Revision: 1.1 $')


def version ():
	''' Return a version number for this module. The version
	    number is computed by multiplying the major CVS revision of
	    each individual component by 1,000, directly adding the minor
	    version, and summing the results.
	'''

	if version.value == None:

		total = 0

		for subversion in versions:
			number = subversion.split ()[1]

			left,right = number.split ('.')
			total += int (left) * 1000
			total += int (right)

		version.value = total

	return version.value


version.value = None
