from __future__ import absolute_import
from . import version
version.append ('$Revision: 90117 $')
del version


from . import get
from . import parser


class Service:

    ''' A Service object is an organizational shortcut to the XML
        associated with every keyword within a given KTL service.

        Typical usage is:

        service_xml = ktlxml.Service (servicename)
        service_xml = ktlxml.Service (servicename, directory=xml_directory)

        keyword_xml = service_xml['keywordname']

        keyword_xml will be a standard XML node.
    '''
    
    keywords = None

    def __init__ (self, service, directory=None):

        name = str (service)
        name = name.strip ()

        if name == '':
            raise ValueError, 'cannot provide XML for an empty service name'


        index = parser.index (name, directory)

        if index == None:
            raise IOError, "cannot locate index.xml for service '%s'" % (name)

        bundles = parser.bundles (name, index, validate=False)
        keywords = parser.dictionary (name, index, validate=False, keyword_bundles=bundles)

        self.bundles = bundles
        self.index = index
        self.keywords = keywords
        self.name = name


    def __contains__ (self, keyword):

        keyword = str (keyword)
        keyword = keyword.upper ()

        return keyword in self.keywords


    def __getitem__ (self, keyword):

        # By convention, keyword names are upper-case.

        keyword = str (keyword)
        keyword = keyword.upper ()

        if keyword in self.keywords:
            return self.keywords[keyword]
        else:
            raise KeyError, "service '%s' does not have a keyword '%s'" % (self.name, keyword)


    def __iter__ (self):
        return ServiceIterator (self)


    def __len__ (self):

        return len (self.keywords)


    def __repr__ (self):

        return "<xml.Service %s>" % repr(self.keywords)


    def __str__ (self):

        return self.name


    def attributes (self, keyword):
        ''' Return a dictionary containing the simple attributes
            of the specified *keyword*.
        '''

        xml = self[keyword]


        if hasattr (xml, 'ktlxml_attributes'):
            pass
        else:
            xml.ktlxml_attributes = buildAttributes (xml)


        return xml.ktlxml_attributes


    def list (self):
        ''' Return a list containing all of the keyword names
            represented by this :class:`Service` instance.
        '''

        keywords = self.keywords.keys ()
        keywords.sort ()

        return keywords

    keys = list
    # keywords = list


# end of class Service



class ServiceIterator:

    def __init__ (self, service):

        self.service = service
        self.keywords = self.service.keywords.keys ()
        self.keywords.sort ()

        # Using pop(), the total iteration time is lower if the
        # list is reversed and elements are popped off the end.
        # The benefit is measurable for services both large and
        # small.

        self.keywords.reverse ()


    def next (self):

        next = None

        while next == None:

            # Using try/except clauses for this sequence of
            # operations is about 10% faster than checking
            # via conditions.

            try:
                # Pop the last keyword off the reversed list.
                keyword = self.keywords.pop ()

            except IndexError:
                # No more keywords to pop.
                raise StopIteration

            try:
                next = self.service[keyword]

            except KeyError:
                next = None

        return next


# end of class ServiceIterator



def buildAttributes (node):
    ''' *node* should be an XML node representing a keyword. Build a
        dictionary of the available attributes of the keyword, using
        key names similar to those for the ktl.Keyword class. If a
        specific attribute is not set in the KTL XML, it is set to
        None.
    '''

    if node.localName != 'keyword':
        raise ValueError, "buildAttributes() requires a <keyword> node, not a <%s> node" % (node.localName)


    attributes = {}

    # Required attributes first.

    attributes['name'] = get.keywordName (node)
    attributes['type'] = get.value (node, 'type')

    # Attributes that may or may not be set, but are valid for
    # all keyword types.

    broadcasts, reads, writes = getCapabilities (node)

    attributes['broadcasts'] = broadcasts
    attributes['reads'] = reads
    attributes['writes'] = writes

    # Attributes that may not be present for this keyword type.

    attributes['enum'] = getEnumerators (node)
    attributes['enumerators'] = attributes['enum']
    attributes['keys'] = getKeys (node)
    attributes['range'] = getRange (node)
    attributes['units'] = getUnits (node)

    return attributes



def getCapabilities (node):

    broadcast = True
    read      = True
    write      = True

    capabilities = node.getElementsByTagName ('capability')

    for capability in capabilities:

        type = capability.getAttribute ('type')

        if type == None:
            continue

        type = type.strip ()
        type = type.lower ()

        value = capability.firstChild.nodeValue
        value = value.strip ()
        value = value.lower ()

        if value == 'true':
            continue

        if type == 'broadcast':
            broadcast = False

        elif type == 'read':
            read = False

        elif type == 'write':
            write = False

    return ((broadcast, read, write))



def getEnumerators (node):

    enumerators = []

    values = node.getElementsByTagName ('values')

    if len (values) == 0:
        return None
    else:
        values = values[0]


    for entry in values.childNodes:

        if entry.nodeName != 'entry':
            continue

        try:
            value = get.value (entry, 'value')
        except ValueError:
            continue

        enumerators.append (value)


    if len (enumerators) == 0:
        enumerators = None

    return enumerators



def getKeys (node):

    keys = []

    elements = node.getElementsByTagName ('elements')

    if len (elements) == 0:
        return None
    else:
        elements = elements[0]


    for entry in elements.childNodes:

        if entry.nodeName != 'entry':
            continue

        try:
            label = get.value (entry, 'label')
        except ValueError:
            continue

        keys.append (label)


    if len (keys) == 0:
        keys = None

    return keys



def getRange (node):

    range = None

    for element in node.childNodes:
        if element.localName == 'range':
            range = element
            break

    if range == None:
        return


    minimum = getMin (range)
    maximum = getMax (range)

    if minimum == None and maximum == None:
        return


    range = {}

    range['minimum'] = minimum
    range['maximum'] = maximum

    return range



def getMin (range):

    try:
        minimum = get.value (range, 'minimum')
    except ValueError:
        return

    try:
        minimum = float (minimum)
    except (TypeError, ValueError):
        minimum = None

    return minimum



def getMax (range):

    try:
        maximum = get.value (range, 'maximum')
    except ValueError:
        return

    try:
        maximum = float (maximum)
    except (TypeError, ValueError):
        maximum = None

    return maximum



def getUnits (node):

    try:
        units = get.value (node, 'units')
    except ValueError:
        units = None

    return units
