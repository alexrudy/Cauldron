
def parse (node):

    name = node.nodeName

    if name == 'bundle':
        return parseBundle (node)
    elif name == 'keyword':
        return parseKeyword (node)
    elif name == 'units':
        return parseUnits (node)
    else:
        raise ValueError, "cannot parse conversions from '%s' node" % (name)


def parseBundle (node):

    # Get conversions at bundle level, and legacy
    # conversions defined in dispatcher/stages.xml

    # Get list of keywords in bundle

    # Invoke parseKeyword for each keyword
    pass


def parseKeyword (node):

    # Get conversions at keyword level

    # invoke parseUnits for additional conversions
    # at <units> level
    pass

def parseUnits (node):

    # Get conversions at <units> level
    pass

def getBundle (node):
    ''' Locate the <bundle> element that is a parent
        (at any depth) of the specified node.
    '''

    while hasattr (node, 'parentNode'):
        node = node.parentNode

        if node.nodeName == 'bundle':
            return node

    raise ValueError, '<bundle> not found'



class Conversion:

    scopes = {'internal': True,
          'specific': True,
          'bundle': True,
          'universal': True}

    def __init__ (self, node, scope, participants):

        if node.nodeName != 'conversion':
            raise ValueError, "node must be a <conversion>, not <%s>" % (node.nodeName)

        if scope in Conversion.scopes:
            pass
        else:
            raise ValueError, "scope must be one of: %s" % (', '.join (Conversion.scopes.keys ()))

        self.node = node
        self.scope = scope
        self.participants = tuple (participants)
        self.type = None


# end of class Conversion



class BundleConversion (Conversion):

    def __init__ (self, node, scope, bundle=None):

        self.bundle = bundle
        Conversion.__init__ (self, node, scope)


    def discover (self):

        if self.bundle == None:
            self.bundle = getBundle (self.node)

        ### iterate through all keywords in the bundle
        ### assess relationships
        ### append to self.participants
# end of class BundleConversion
