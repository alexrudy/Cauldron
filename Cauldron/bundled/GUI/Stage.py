import version
version.append ('$Revision: 91488 $')
del version


import ktl
import traceback

import Log


# Are motors expected to be powered and hold position when not in motion?
# This is matched against the ascii value of the STAGEMOO keyword, which
# is expected to be 'on' or 'off'.
#
# Use the helper function GUI.setMotorHold() to modify this value.
#
# If the stage has a STAGEMOE keyword, that will be honored first, and
# any GUI-specific servo_hold value will be ignored.

servo_hold = False


# Which STAGESTA values should be considered as natural STAGESTA values
# where the stage's motor would be powered?

powered =  {'calibrating': True,
	    'stopping': True,
	    'moving': True,
	    'jogging': True,
	    'slewing': True,
	    'acquiring': True,
	    'tracking': True,
	    'local/jogging': True}


# List of dispatcher-2-style stages. This list will be used for actions
# such as recalibrating all stages, or stopping all stages.

stages = []

# Separators that will be used to build RON/PEN values, or any other
# keyword that allows arbitrary separators. This is a concatenation
# of string.whitespace and string.punctuation; @ is almost always
# acceptable, so it got moved to the front of the line.

separators = '@\t\n\x0b\x0c\r !"#$%&\'()*+,-./:;<=>?[\\]^_`{|}~'



def setStages (sequence=None, scan=None):
	''' Define the 'global' list of stages that will be iterated over
	    by some of the helper functions, such as calibrateAll().
	    Alternatively, if *scan* is specified, inspect that ktl.Service
	    instance for defined stages.
	'''

	if sequence != None:
		sequence = list (sequence)
	else:
		sequence = []


	if scan != None:
		# Look for 'DISP*_MOTOR' keywords. These define a mapping
		# between motor axes and stage names.

		prefix = 'DISP'
		suffix = '_MOTOR'
		len_prefix = len (prefix)
		len_suffix = len (suffix)

		failure = False

		for keyword in scan.list ():

			keyword_prefix = keyword[:len_prefix]
			keyword_suffix = keyword[-len_suffix:]

			if keyword_prefix != prefix or keyword_suffix != suffix:
			   	continue

			else:
				dispatcher = keyword[len_prefix:-len_suffix]

				try:
					int (dispatcher)
				except ValueError:
					continue


			# It's a match.

			try:
				mapping = scan[keyword]['ascii']
			except:
				# Retrieving the ascii value should not
				# raise an exception. Skip this broken
				# keyword, and continue.

				failure = True
				continue

			mapping = scan[keyword]['ascii'].split ()

			for value in mapping:

				if len (value) < 2:
					# Axis name (A, B, C, etc.)
					continue

				sequence.append (value)

		setStages.scan_failure = failure


	global stages
	stages = tuple (sequence)


setStages.scan_failure = None


def setMotorHold (value):

	if value == True or value == False:
		pass
	else:
		raise TypeError, 'setMotorHold argument must be a boolean'

	global servo_hold
	servo_hold = value


#
# #
# Functions for parsing and setting PEN/RON values.
# #
#


def sortRON (triplet1, triplet2):
	''' Used to sort a list of RON triplets by ordinal number,
	    which is the second field of the three.
	'''

	ordinal1 = int (triplet1[1])
	ordinal2 = int (triplet2[1])

	if ordinal1 < ordinal2:
		return -1

	if ordinal1 > ordinal2:
		return 1

	raise ValueError, 'two distinct RON triplets cannot have the same ordinal value'



def createPEN (values):
	''' Create a legal PEN value from a properly ordered
	    list of values, and return it as a string.
	'''

	remainder = len (values) % 2

	if remainder != 0:
		raise ValueError, 'quantity of values in a PEN must be divisible by two'

	concatenated = ''.join (values)

	# Find an acceptable separator.

	separator = None

	for character in separators:
		if character in concatenated:
			continue
		else:
			separator = character
			break

	if separator == None:
		raise ValueError, 'unable to find a separator for PEN value'

	# Assemble the PEN value.

	new_value = "%s%s" % (separator, separator.join (values))

	return new_value



def createRON (values):
	''' Create a legal RON value from a properly ordered
	    list of values, and return it as a string.
	'''

	remainder = len (values) % 3

	if remainder != 0:
		raise ValueError, 'quantity of values in a RON must be divisible by three'

	concatenated = ''.join (values)

	# Find an acceptable separator.

	separator = None

	for character in separators:
		if character in concatenated:
			continue
		else:
			separator = character
			break

	if separator == None:
		raise ValueError, 'unable to find a separator for RON keyword'

	# Assemble the RON value.

	new_value = "%s%s" % (separator, separator.join (values))

	return new_value



def parseNMS (value):
	''' Parse an NMS keyword value into a list of NAM
	    values; the list is the return result.
	'''

	if type (value) != str:
		raise TypeError, 'NMS keyword value must be a string'

	# Empty value means no pairs.

	if len (value) == 0 or len (value) == 1:
		return ()

	# If we got here, there's at least a separator present.

	separator = value[0]

	fields = value.split (separator)

	# The first value should be an empty string, due to the
	# leading separator.

	if fields[0] == '':
		fields = fields[1:]
	else:
		raise RuntimeError, 'unexpected behavior from split ()-- this should not occur'


	# All we should have left now are the names.

	return tuple (fields)



def parsePEN (value):
	''' Parse a PEN keyword value into a list of POS/NAM
	    pairs; the list is the return result.
	'''

	if type (value) != str:
		raise TypeError, 'PEN keyword value must be a string'

	pairs = []

	# Empty value means no pairs.

	if len (value) == 0 or len (value) == 1:
		return pairs

	# If we got here, there's at least a separator present.

	separator = value[0]

	fields = value.split (separator)

	# The first value should be an empty string, due to the
	# leading separator.

	if fields[0] == '':
		fields = fields[1:]
	else:
		raise RuntimeError, 'unexpected behavior from split ()-- this should not occur'


	# All we should have left now are the value pairs.

	remainder = len (fields) % 2

	if remainder != 0:
		raise ValueError, 'quantity of values in a PEN must be divisble by two'

	pair = []

	for field in fields:

		if len (pair) == 2:
			pairs.append (pair)
			pair = []

		pair.append (field)

	# Catch the last one, if any:

	if len (pair) == 2:
		pairs.append (pair)

	return pairs



def parseRON (value):
	''' Parse a RON keyword value into a list of RAW/ORD/NAM
	    triplets; the list is the return result.
	'''

	if type (value) != str:
		raise TypeError, 'RON keyword value must be a string'

	triplets = []

	# Empty value means no triplets.

	if len (value) == 0 or len (value) == 1:
		return triplets

	# If we got here, there's at least a separator present.

	separator = value[0]

	fields = value.split (separator)

	# The first value should be an empty string, due to the
	# leading separator.

	if fields[0] == '':
		fields = fields[1:]
	else:
		raise RuntimeError, 'unexpected behavior from split ()-- this should not occur'


	# All we should have left now are the triplets.

	remainder = len (fields) % 3

	if remainder != 0:
		raise ValueError, 'quantity of values in a RON must be divisble by three'

	triplet = []

	for field in fields:

		if len (triplet) == 3:
			triplets.append (triplet)
			triplet = []

		triplet.append (field)

	# Catch the last one, if any:

	if len (triplet) == 3:
		triplets.append (triplet)

	triplets.sort (sortRON)

	return triplets


#
# #
# Typical keyword callbacks for different stage and value types.
# #
#

def virtCallbacks (stage, service):

	button = stage.button
	value = stage.value
	stage = stage.stage

	err = stage + 'ERR'
	lck = stage + 'LCK'
	pos = stage + 'POS'
	sta = stage + 'STA'

	for keyword in (err, lck, sta):
		if keyword in service:
			button.setCallback (service[keyword])

	value.setKeyword (service[pos])
	button.setService (service)



def menuCallbacks (stage, service):

	button = stage.button
	value = stage.value
	stage = stage.stage

	err = stage + 'ERR'
	lck = stage + 'LCK'
	lim = stage + 'LIM'
	moe = stage + 'MOE'
	moo = stage + 'MOO'
	nam = stage + 'NAM'
	nms = stage + 'NMS'
	npx = stage + 'NPX'
	ord = stage + 'ORD'
	pen = stage + 'PEN'
	rel = stage + 'REL'
	ron = stage + 'RON'
	sta = stage + 'STA'
	trl = stage + 'TRL'

	for keyword in (err, lck, lim, moe, moo, ord, rel, sta, trl):
		if keyword in service:
			button.setCallback (service[keyword])

	if npx in service:
		value.setCallback (service[npx])

	found_menu = None
	for keyword in (nms, pen, ron):
		if keyword in service:
			if found_menu == None:
				found_menu = keyword
				value.setCallback (service[keyword])
			else:
				raise RuntimeError, "stage '%s' has both a '%s' and '%s' keyword" % (stage, found_menu, keyword)

	value.setKeyword (service[nam])
	button.setService (service)



def rawCallbacks (stage, service):
	''' Display the RAW.
	'''

	button = stage.button
	value = stage.value
	stage = stage.stage

	err = stage + 'ERR'
	lck = stage + 'LCK'
	lim = stage + 'LIM'
	moe = stage + 'MOE'
	moo = stage + 'MOO'
	raw = stage + 'RAW'
	rel = stage + 'REL'
	sta = stage + 'STA'
	trl = stage + 'TRL'

	for keyword in (err, lck, lim, moe, moo, rel, sta, trl):
		if keyword in service:
			button.setCallback (service[keyword])

	value.setKeyword (service[raw])
	button.setService (service)



def valCallbacks (stage, service):
	''' Use VAL instead of RAW.
	'''

	button = stage.button
	value = stage.value
	stage = stage.stage

	err = stage + 'ERR'
	lck = stage + 'LCK'
	lim = stage + 'LIM'
	moe = stage + 'MOE'
	moo = stage + 'MOO'
	rel = stage + 'REL'
	sta = stage + 'STA'
	trl = stage + 'TRL'
	val = stage + 'VAL'

	for keyword in (err, lck, lim, moe, moo, rel, sta, trl):
		if keyword in service:
			button.setCallback (service[keyword])

	value.setKeyword (service[val])
	button.setService (service)



def vaxCallbacks (stage, service):
	''' Use VAX instead of RAW.
	'''

	button = stage.button
	value = stage.value
	stage = stage.stage

	err = stage + 'ERR'
	lck = stage + 'LCK'
	lim = stage + 'LIM'
	moe = stage + 'MOE'
	moo = stage + 'MOO'
	rel = stage + 'REL'
	sta = stage + 'STA'
	trl = stage + 'TRL'
	vax = stage + 'VAX'

	for keyword in (err, lck, lim, moe, moo, rel, sta, trl):
		if keyword in service:
			button.setCallback (service[keyword])

	value.setKeyword (service[vax])
	button.setService (service)



def calibrateAll (service, force=False):
	''' Re-calibrate all stages. If force=True, all stages will be
	    re-calibrated, rather than just the ones that are not already
	    calibrated.
	'''

	if setStages.scan_failure == True:
		setStages (scan=service)

	for stage in stages:
		try:
			calibrate (stage, service, force)
		except ktl.ktlError:
			Log.alert ("Stage '%s' failed to calibrate" % (stage))
			Log.error (traceback.format_exc ())


def calibrate (stage, service, force=False):
	''' Calibrate a single stage. If force=True, the stage will
	    be re-calibrated even if it is reporting that it is already
	    calibrated.

	    This function relies on the MOD and CAL keywords being
	    monitored before this function is called.
	'''

	timeout = 5

	mode  = "%sMOD" % (stage)
	homed = "%sCAL" % (stage)

	if homed in service:
		homed = service[homed]
	else:
		# No calibrate keyword. Nothing to do.
		return

	try:
		mode = service[mode]
	except KeyError:
		mode = None

	try:
		homed_value = homed['ascii']
	except ktl.ktlError:
		homed_value = homed.read ()

	homed_value = homed_value.lower ()

	if force == True and homed_value != 'reset':
		# Force a calibration to occur by first writing 'reset'
		# to the keyword. Use a timeout on the blocking write,
		# which is only effective if the keyword/service supports
		# KTL_NOTIFY writes.

		try:
			homed.write ('reset', wait=True, timeout=timeout)

		except ktl.TimeoutException:
			Log.alert ("writing 'reset' to %s timed out after %d seconds" % (homed['name'], timeout))
			return

		except ktl.ktlError:
			Log.alert ("writing 'reset' to %s failed:\n%s" % (homed['name'], traceback.format_exc ()))
			return


	if force == True or homed_value != 'homed':

		if mode != None:
			try:
				mode_value = mode['ascii']
			except ktl.ktlError:
				mode_value = mode.read ()

			# Only look at the first three characters of the mode,
			# since it could be 'pos on' or 'pos off', not just
			# 'pos'.

			mode_value = mode_value[:3].lower ()

			if mode_value != 'pos':
				# We need to wait for the mode to change
				# before proceeding; do a wait write.

				try:
					mode.write ('pos', wait=True, timeout=timeout)

				except ktl.TimeoutException:
					Log.alert ("writing 'pos' to %s timed out after %d seconds" % (mode['name'], timeout))
					return

				except ktl.ktlError:
					Log.alert ("writing 'pos' to %s failed:\n%s"% (mode['name'], traceback.format_exc ()))
					return


		# Having checked the mode (if available), now perform
		# the calibration.

		homed.write ('homed', wait=False)



def stop (stage, service):
	''' Using the STP keyword, immediately stop motion on
	    the designated stage.
	'''

	stop = "%sSTP" % (stage)
	stop = service[stop]

	message = "Immediate stop request via %s GUI" % (service.name)

	stop.write (message, wait=False)



def stopAll (service):
	''' Using all available STP keywords, immediately stop motion on
	    all available stages.
	'''

	if setStages.scan_failure == True:
		setStages (scan=True)

	for stage in stages:
		stop (stage, service)

