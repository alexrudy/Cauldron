from __future__ import absolute_import
from . import version
version.append ('$Revision: 85832 $')
del version


import os


def dispatcher (node):
    ''' Return the <dispatcher> node associated with the designated
        keyword node.
    '''

    while node != None:
        try:
            dispatcher = node.ktlxml_dispatcher
            found = True
        except AttributeError:
            found = False

        if found == True:
            return dispatcher

        try:
            node = node.parentNode
        except AttributeError:
            node = None

    return None



def filename (node):
    ''' Retrieve the filename from whence the designated XML node
        was retrieved. Processing is nearly identical to keywordName().
    '''

    while node != None:
        try:
            file = node.ktlxml_filename
            found = True
        except AttributeError:
            found = False

        if found == True:
            return file

        try:
            node = node.parentNode
        except AttributeError:
            node = None

    return None



def keywordName (node):
    ''' Return the keyword name associated with the designated node.
        The node can be any child of a <keyword> node, this function
        will traverse upwards until it finds a ktlxml_keyword_name
        attribute, as set when the XML is first loaded by the
        bundles() function.

        By storing the keyword name outside of the ktlxml_simple_values
        dictionary used by getValue(), we ensure that we correctly
        return the keyword name, rather than the value of some other
        <name> element associated with a child node.
    '''

    while node != None:
        try:
            name = node.ktlxml_keyword_name
            found = True
        except AttributeError:
            found = False

        if found == True:
            return name

        try:
            node = node.parentNode
        except AttributeError:
            node = None

    return None



def value (node, name, strip=True):
    ''' For a given XML node, retrieve a single (non-nested)
        simple child node (with name 'name', and return its
        value as a whitespace-stripped string.

        Set strip=False to prevent automatic whitespace removal.
    '''

    # Values are cached in case of repetitve processing.
    # This prevents an order(N) traversal of the node
    # for repetitive queries.

    try:
        cache = node.ktlxml_simple_values
    except AttributeError:
        cache = {}
        node.ktlxml_simple_values = cache


    try:
        value = cache[name]
    except KeyError:
        pass
    else:
        if isinstance (value, Exception):
            raise value

        if strip == True:
            value = value.strip ()

        return value



    found_nodes = []

    for entry in node.childNodes:
        if entry.nodeName == name:
            found_nodes.append (entry)

    if len (found_nodes) == 1:
        exception = None
    else:
        keyword = keywordName (node)
        file = filename (node)

        if keyword == None:
            keyword = '???'

        if file == None:
            file = '???'
        else:
            file = os.path.basename (file)

        if len (found_nodes) == 0:
            exception = ValueError ("<%s> has no <%s> child (keyword %s, file %s)" % (node.nodeName, name, keyword, file))

        else:
            exception = ValueError ("<%s> has %d <%s> children (expected one, keyword %s, file %s)" % (node.nodeName, len (found_nodes), name, keyword, file))


    if exception != None:

        # Cache the negative result, and raise the exception.

        cache[name] = exception
        raise exception


    # Otherwise, exactly one node was found. It should have exactly
    # one child node; if there are zero, there is no value. If there
    # are extra children, it is a complex element.

    found_node = found_nodes[0]

    if len (found_node.childNodes) == 1:
        exception = None

    else:
        keyword = keywordName (node)
        file = filename (node)

        if keyword == None:
            keyword = '???'

        if file == None:
            file = '???'
        else:
            file = os.path.basename (file)

        if len (found_node.childNodes) == 0:
            exception = ValueError ("<%s> has no value (keyword %s, file %s)" % (name, keyword, file))
        else:
            exception = ValueError ("<%s> is complex with %d child nodes (keyword %s, file %s)" % (name, len (found_node.childNodes), keyword, file))

    if exception != None:

        # Cache the negative result, and raise the exception.

        cache[name] = exception
        raise exception


    value = found_node.firstChild.nodeValue

    # Cache the positive result.

    cache[name] = value


    # In simple XML, whitespace around a value is not supposed
    # to be significant. This can be controlled by a schema,
    # however, which may designate that whitespace *is* significant.

    if strip == True:
        value = value.strip ()

    return value


