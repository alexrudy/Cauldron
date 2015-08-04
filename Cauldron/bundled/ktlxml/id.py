import version
version.append ('$Revision: 83731 $')
del version


# Python changed the layout of hash modules in Python 2.5, but our
# typical minimum Python version is 2.4.

try:
    # Python 2.5 and up.
    import hashlib
    shaHash = hashlib.sha1

except ImportError:
    # Python 2.4 and below.
    import sha
    shaHash = sha.new


def generate (service, keyword):
    ''' Hash a service and keyword name down to a 32-bit integer
        representation. The fundamental hash is SHA-1, for portability
        reasons. The resulting hash will always be between 1 and
        2147483647, suitable for use as a KTL keyword ID number,
        and should be reliably unique for any typical usage.
    '''

    # Sanity checks.

    if isinstance (service, str) or isinstance (service, unicode):
        pass
    elif hasattr (service, 'name'):
        # Might be a ktl.Service instance.
        service = service.name
    else:
        raise ValueError, 'service must be specified as a string'

    if isinstance (keyword, str) or isinstance (keyword, unicode):
        pass
    else:
        # Might be a ktl.Keyword instance.
        try:
            keyword = keyword['name']
        except:
            raise ValueError, 'keyword must be specified as a string'

    # KTL service names are case-significant. For the purpose of
    # generating a keyword ID number, we ignore that possibility.

    service = service.strip ()
    service = service.lower ()

    # KTL keyword names are case-insignificant.

    keyword = keyword.strip ()
    keyword = keyword.upper ()

    if len (keyword) == 0:
        raise ValueError, "the empty string is not a valid keyword name"


    # Begin hashing.

    service = shaHash (service)
    service = service.hexdigest ()
    service = int (service, 16)
    service = service % generate.max_service

    keyword = shaHash (keyword)
    keyword = keyword.hexdigest ()
    keyword = int (keyword, 16)
    keyword = keyword % generate.max_keyword

    service  = service << generate.service_shift
    combined = service + keyword

    if combined > generate.max:
        # This should never happen.
        raise RuntimeError, "keyword id (%d) exceeds ktlxml.generate.max" % (combined)

    # Minimum return value is one. It is possible for the above
    # to result in a minimum value of zero.

    if combined == 0:
        combined = 1

    return combined



# Establish the range of allowed keyword id values.

generate.max         = 2147483647    # 0b01111111111111111111111111111111
generate.max_service = 15        # 0b00000000000000000000000000001111
generate.max_keyword = 134217727    # 0b00000111111111111111111111111111

# How many bits to shift generate.max_service in order to not overlap
# with generate.max_keyword.

generate.service_shift = 27
