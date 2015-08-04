from . import version
version.append ('$Revision: 85832 $')
del version

from . import get

import xml.dom.minidom
import os
import sys


def index (service, directory=None):
    ''' For a given service name, locate the appropriate index.xml,
        and return its absolute filename. Note that the service name
        is not case-sensitive, though one could make the argument that
        a KTL service is traditionally case-sensitive.

        If a directory is specified, the directory will be checked
        to see if it contains an index.xml for the requested service.
        For typical use, the directory would be the KROOT DATSUB used
        to install the xml describing the service in question, or
        an absolute path to the same, or an otherwise valid path
        from the current working directory. Note that the directory
        is case-sensitive.

        It is also legal for the specified directory to be a relative
        path from $RELDIR/data.

        If a directory is not specified, the default locations are:

        $RELDIR/data/service
        $RELDIR/data/service/xml

        Note that these default locations *are* case-sensitive with
        respect to the supplied service name.

        If $LROOT is defined, $LROOT will be checked after the same
        fashion as the $RELDIR checks above. Note that any matches in
        $LROOT will take precedence over matches in $RELDIR.

        If a match is found in both $LROOT and $RELDIR, a ValueError
        exception will be raised.

        Returns None if no matching service/index.xml can be found.
    '''

    service = str (service)

    if service == '':
        raise ValueError, "cannot search for an empty service name"


    directories = []


    reldir_data = os.path.join (os.environ['RELDIR'], 'data')

    try:
        lroot = os.environ['LROOT']
    except KeyError:
        lroot = None
        lroot_data = None

    if lroot != None:
        lroot_data = os.path.join (lroot, 'data')


    # Use the specified directory as the first location to check.

    if directory != None:

        original = directory
        exists = False

        if os.path.isabs (directory) or \
           os.path.isdir (directory):
            # Valid path. No modification required.
            pass
        else:
            if lroot_data != None:
                lroot_directory = os.path.join (lroot_data, directory)
                if os.path.isdir (lroot_directory):
                    directories.append (lroot_directory)
                    exists = True

                lroot_directory = os.path.join (lroot_directory, 'xml')
                if os.path.isdir (lroot_directory):
                    directories.append (lroot_directory)
                    exists = True

            directory = os.path.join (reldir_data, directory)

        if os.path.isdir (directory):
            directories.append (directory)
            exists = True

        directory = os.path.join (directory, 'xml')

        if os.path.isdir (directory):
            directories.append (directory)
            exists = True

        if exists == False:
            raise OSError, "directory '%s' does not exist" % (original)


    else:
        # Append the default search directories to the otherwise
        # empty list.

        if lroot_data != None:
            directory = os.path.join (lroot_data, service)
            directories.append (directory)

            directory = os.path.join (directory, 'xml')
            directories.append (directory)

        directory = os.path.join (reldir_data, service)
        directories.append (directory)

        directory = os.path.join (directory, 'xml')
        directories.append (directory)


    # We're going to be case-insensitive about the service name from
    # here on out.

    service = service.lower ()

    # Iterate through the available directories.

    match = None

    for directory in directories:

        if os.path.isdir (directory):
            pass
        else:
            # Do not process a directory that does not exist.
            continue

        # Check for an index.xml file here.

        filename = os.path.join (directory, 'index.xml')

        if os.path.isfile (filename):
            pass
        else:
            continue

        # Check to see whether this file is for the correct service.

        try:
            index_xml = xml.dom.minidom.parse (filename)
        except xml.parsers.expat.ExpatError:
            # Log the error, and move on to the next filename,
            # if any.

            exception, value, traceback = sys.exc_info ()

            sys.stderr.write ("Error parsing xml file '%s':\n" % (filename))
            sys.stderr.write (str (value) + '\n')

            continue


        index_node = index_xml.childNodes[0]
        # If the root node is not 'index', this is not an index.xml
        # file that we're familiar with.

        if index_node.nodeName != 'index':
            continue

        # Check the 'service' attribute of the root index node.

        index_service = index_node.getAttributeNode ('service')

        if index_service == None:
            raise ValueError, "the root index node in file '%s' does not have a 'service' attribute" % (filename)

        index_service = index_service.value
        index_service = index_service.lower ()
        index_service = index_service.strip ()

        if str(index_service) == service:
            if match == None:
                match = filename
            else:
                raise ValueError, "multiple service index.xml files found for service '%s':\n    %s\n    %s" % (service, match, filename)


    # Return what we found, even if it was nothing.

    return match



def includes (filename, recurse=True):
    ''' Return a dictionary of index.xml locations for any/all services
        included in the specified index.xml file. :func:`includes` will
        recursively discover services included within other services.
    '''

    try:
        index_xml = xml.dom.minidom.parse (filename)
    except xml.parsers.expat.ExpatError:
        # Add in the file containing the error to the exception value.

        exception, value, traceback = sys.exc_info ()

        value = "%s: %s" % (filename, value)
        raise xml.parsers.expat.ExpatError, value, traceback


    discovered = {}
    included = index_xml.getElementsByTagName ('include')

    for include_node in included:

        include_type = include_node.getAttributeNode ('type')

        if include_type == None:
            # Assume type is 'service'.
            pass
        else:
            include_type = include_type.value
            include_type = include_type.strip ()
            include_type = include_type.lower ()

            if include_type == 'service':
                pass
            else:
                raise ValueError, "unknown include type '%s' for service '%s'" % (include_type, service)


        # Acquire the name of the service to include, and
        # then acquire the index location for that service.

        include_name = include_node.firstChild.nodeValue.strip ()

        # First confirm that the service to include is not our own
        # service name.

        if include_name in discovered:
            raise ValueError, "included service '%s' included multiple times" % (include_name)

        include_index = index (include_name)

        discovered[include_name] = include_index


        if recurse == False:
            continue

        # Now check for any nested includes in this included service.

        nested_includes = includes (include_index)

        for nested_name in nested_includes:

            if nested_name in discovered:
                raise ValueError, "nested included service '%s' included multiple times (via service %s)" % (nested_name, include_name)

            discovered[nested_name] = nested_includes[nested_name]


    return discovered



def bundles (service, filename=None, validate=True):
    ''' Return a dictionary of XML nodes corresponding to
        the keyword bundles in the designated service.

        The optional 'filename' argument should be an
        valid path to the appropriate index.xml for this
        service. ktlxml.index () is invoked to validate
        the selection, if any. If you do not want to
        validate the specified filename, set the 'validate'
        argument to False.

        If the filename is not specified, ktlxml.index ()
        is invoked to discover the appropriate filename
        for the designated service, if it can be located.
    '''

    if filename == None:
        directory = None
    else:
        directory = os.path.dirname (filename)

    if filename != None and validate == False:
        # If the user said don't check the filename,
        # don't check the filename.

        pass
    else:
        # Otherwise, leverage ktlxml.index() to ensure
        # that the specified index, if any, is minimally
        # valid; this step will also trigger if no filename
        # is specified, thus, we will search the default
        # locations per the logic in ktlxml.index().

        filename = index (service, directory)

    if filename == None:
        raise IOError, "cannot locate index.xml for service '%s'" % (service)


    service = service.lower ()
    index_filename = filename


    # Acquire the list of files associated with this service.

    try:
        index_xml = xml.dom.minidom.parse (index_filename)
    except xml.parsers.expat.ExpatError:
        # Add in the file containing the error to the exception value.

        exception, value, traceback = sys.exc_info ()

        value = "%s: %s" % (index_filename, value)
        raise xml.parsers.expat.ExpatError, value, traceback

    xml_files = index_xml.getElementsByTagName ('files')

    if len (xml_files) == 1:
        xml_files = xml_files[0]

    elif len (xml_files) == 0:
        # Hopefully, there are includes that will be processed
        # later on. Otherwise, there will be no XML content for
        # this service.

        xml_files = None

    elif len (xml_files) > 1:
        raise ValueError, "there should not be more than one 'files' element in the index.xml"


    # Get the individual 'file' elements within the 'files' element.

    if xml_files != None:
        xml_files = xml_files.getElementsByTagName ('file')
    else:
        xml_files = ()

    filenames = []

    for xml_file in xml_files:
        filename = get.value (xml_file, 'location')
    
        if os.path.isabs (filename):
            # No manipulation necessary.
            pass
        else:
            # If paths are relative, they should be relative
            # to the index.xml location.

            directory = os.path.dirname (index_filename)
            filename  = os.path.join (directory, filename)

        filenames.append (filename)

    filenames.sort ()

    keyword_bundles = {}

    for filename in filenames:
        try:
            bundle_xml = xml.dom.minidom.parse (filename)
        except xml.parsers.expat.ExpatError:
            # Add in the file containing the error to the
            # exception value.

            exception, value, traceback = sys.exc_info ()

            value = "%s: %s" % (filename, value)
            raise xml.parsers.expat.ExpatError, value, traceback


        bundle_node = bundle_xml.childNodes[0]

        if bundle_node.localName != 'bundle':
            # Skip files that don't contain bundles.
            continue

        bundle_service = bundle_node.getAttributeNode ('service')

        if bundle_service == None:
            raise ValueError, "the root bundle node in file '%s' does not have a 'service' attribute" % (filename)

        bundle_service = bundle_service.value.strip ()
        bundle_service = bundle_service.lower ()

        if bundle_service != service:
            # There shouldn't be bundles not affiliated with
            # this specific service.

            raise ValueError, "bundle in '%s' is for service '%s', not '%s'" % (filename, bundle_service, service)


        bundle_name = bundle_node.getAttributeNode ('name')

        if bundle_name == None:
            # Use the filename instead. We just need a unique
            # identifier, the name is not otherwise significant.

            bundle_name = filename

        else:
            bundle_name = bundle_name.value.strip ()
            bundle_name = bundle_name.lower ()

        if bundle_name in keyword_bundles:
            # Bundles cannot have duplicate names.

            raise ValueError, "bundle in '%s' has duplicate bundle name '%s'" % (filename, bundle_name)


        # Retain the filename for later reference, largely for
        # error messages.

        bundle_node.ktlxml_filename = filename

        keyword_bundles[bundle_name] = bundle_node

        # For the benefit of future error reporting, find all
        # keyword names now. It is required that all <keyword>
        # elements have a simple <name> element. As part of the
        # process, find the dispatcher element, and associate it
        # with the bundle.
        #
        # There is no real speed penalty to doing this processing
        # now, as the initial loading of the XML is overwhelmingly
        # the most expensive part of the process.

        found_keywords = []
        dispatcher_node = None

        for keyword_node in bundle_node.childNodes:

            if keyword_node.localName == 'dispatcher':
                dispatcher_node = keyword_node
                continue

            if keyword_node.localName != 'keyword':
                # Go to the next node, we only
                # pay attention to keyword nodes.
                continue

            keyword_name = get.value (keyword_node, 'name')
            keyword_name = keyword_name.upper ()

            keyword_node.ktlxml_keyword_name = keyword_name
            found_keywords.append (keyword_node)


        bundle_node.ktlxml_dispatcher = dispatcher_node



    # That concludes our parsing of the service-specific bundle defintions.
    # It is possible that the XML designates one or more other XML locations
    # from which contents may be inherited.

    included = includes (index_filename, recurse=False)

    for include_name in included.keys ():

        if include_name.lower () == service:
            raise ValueError, "included service is the same as the local service ('%s')" % (service)


        # Invoke ktlxml.bundles() recursively to retrieve
        # the keyword data for the included service.

        included_bundles = bundles (include_name)

        # Insert each included bundle into our existing
        # set of bundles, watching for collisions. Insert
        # included bundles as "servicename.bundlename" to
        # both avoid potential collisions, and to provide
        # feedback about the origins of the bundle.

        for bundle in included_bundles.keys ():

            insert_name = "%s:%s" % (include_name, bundle)

            if insert_name in keyword_bundles:
                raise ValueError, "included service '%s' has a duplicate bundle name '%s'" % (include_name, insert_name)

            bundle = included_bundles[bundle]

            keyword_bundles[insert_name] = bundle


    # That's everything. Return the dictionary as constructed.

    return keyword_bundles



def dictionary (service, filename=None, validate=True, keyword_bundles=None):
    ''' Return a dictionary of XML nodes corresponding to
        the keywords in the designated service.

        The 'service', 'filename', and 'validate' arguments
        are passed directly to ktlxml.bundles (). If the
        'keyword_bundles' argument is specified, no call
        will be made to ktlxml.bundles (), and the supplied
        dictionary will be used directly.
    '''

    keywords = {}

    if keyword_bundles == None:
        keyword_bundles = bundles (service, filename, validate)

    bundle_names = keyword_bundles.keys ()
    bundle_names.sort ()

    for bundle_name in bundle_names:
        bundle_node = keyword_bundles[bundle_name]

        bundle_id = bundle_node.getAttributeNode ('id')

        if bundle_id == None:
            bundle_id = 0
        else:    
            bundle_id = int (bundle_id.value.strip ())

        for keyword_node in bundle_node.childNodes:

            if keyword_node.localName != 'keyword':
                # Go to the next node, we only
                # pay attention to keyword nodes.
                continue

            keyword_name = keyword_node.ktlxml_keyword_name

            # If it exists, augment the keyword_id value
            # by the bundle_id value.

            keyword_id = keyword_node.getAttributeNode ('id')

            if keyword_id != None:
                keyword_id = int (keyword_id.value.strip ())

                keyword_id = bundle_id + keyword_id
                keyword_id = str (keyword_id)

                keyword_node.setAttribute ('id', keyword_id)

            if keyword_name in keywords:
                raise ValueError, "XML for service '%s' has more than one keyword '%s'" % (service, keyword_name)

            keywords[keyword_name] = keyword_node


    # Dictionary fully constructed.

    return keywords
