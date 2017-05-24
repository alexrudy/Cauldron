# -*- coding: utf-8 -*-
"""
This module handles functions which interact with KTL XML.
"""
from functools import wraps
    
from ..exc import CauldronXMLWarning, WrongDispatcher, CauldronWarning
from ..extern import ktlxml
from ..api import STRICT_KTL_XML, WARN_KTL_XML, WARNINGS_KTL

ktlxml_get = None
try:
    ktlxml_get = getattr(ktlxml, 'get')
except:
    try:
        ktlxml_get = getattr(ktlxml, 'Get')
    except:
        pass

__all__ = ['get_dispatcher_XML', 'get_initial_XML', 'get_units_xml', 'init_xml']

def xml(msg="KTLXML raised an error. Exception was {exc!s}.", bound=False):
    """A wrapper for XML functions."""
    def decorate(f):
        @wraps(f)
        def decorator(self, *args, **kwargs):
            try:
                if bound:
                    result = f(self, *args, **kwargs)
                else:
                    result = f(*args, **kwargs)
            except Exception as exc:
                if STRICT_KTL_XML:
                    raise
                emit_xml_warning(self.log, msg.format(self=self, exc=exc))
            else:
                return result
        return decorator
    return decorate

@xml("KTLXML was not loaded correctly for service {self.name:s}. Keywords will not be validated against XML. Exception was {exc!s}.", bound=True)
def init_xml(service):
    """Return a ktlxml Service object"""
    try:
        service.xml = ktlxml.Service(service.name)
    except IOError as e:
        if (not STRICT_KTL_XML) and str(e).startswith("cannot locate index.xml for service"):
            emit_xml_warning(service.log, "Could not locate index.xml for service {self.name:s}. Keywords will not be validated against XML.".format(self=service), exc_info=False)
        else:
            raise
    except Exception as e:
        raise
    else:
        for keyword in service.xml.list():
            if service.dispatcher == get_dispatcher_XML(service, keyword):
                service._keywords[keyword] = None

def get_dispatcher_XML(service, name):
    """Check that the XML for the dispatcher is correct.
    
    Checks that if this service has a dispatcher value, that it
    matches the keyword's dispatcher value.
    """
    if service.dispatcher != None:
        keyword_node = service.xml[name]
        dispatcher_node = ktlxml_get.dispatcher(keyword_node)
        dispatcher = ktlxml_get.value(dispatcher_node, 'name')
        return dispatcher
    return None

def get_initial_XML(xml, name):
    """Get the keyword's initial value from the XML configuraton.
    
    :param xml: The XML tree containing keywords.
    :param name: Name of the keyword.
    """
    keyword_xml = xml[name]
    
    initial = None
    
    for element in keyword_xml.childNodes:
        if element.nodeName != 'serverside' and \
           element.nodeName != 'server-side':
            continue
            
        server_xml = element
        
        for element in server_xml.childNodes:
            if element.nodeName != 'initialize':
                continue
                
            # TODO: this loop could check to see if
            # there is more than one initial value,
            # rather than immediately halting the
            # iteration.
            
            try:
                initial = ktlxml.getValue (element, 'value')
            except ValueError: # pragma: no cover
                continue
                
            # Found a value, stop the iteration.
            break
            
            
        if initial != None:
            # Found a value, stop the iteration.
            break
            
    return initial
    
@xml("XML setup for keyword '{self.name}' failed. Exception was {exc!s}")
def get_initial_value(service, name, initial):
    """docstring for get_initial_value"""
    try:
        if service.xml is not None:
            dispatcher = get_dispatcher_XML(service, name)
            if dispatcher != service.dispatcher:
                if STRICT_KTL_XML:
                    raise WrongDispatcher("service dispatcher is '%s', dispatcher for %s is '%s'" % (service.dispatcher, name, dispatcher))
            if initial is None:
                initial = get_initial_XML(service.xml, name)
    except WrongDispatcher:
        if STRICT_KTL_XML:
            raise
        msg = "Service {0} dispatcher '{1}' does not match keyword {2} dispatcher '{3}'".format(service.name, service.dispatcher, name, dispatcher)
        emit_xml_warning(msg)
    return initial
   

@xml("XML setup for orphan keyword in service {self.name:s} failed. Exception {exc!s}", bound=True)
def setup_orphan(service, name):
    """Set up orphans, respecting XML."""
    from Cauldron import DFW
    try:
        xml = service.xml[name]
        ktl_type = ktlxml.getValue(xml, 'type')
        cls = DFW.Keyword.types[ktl_type]
    except Exception as e:
        if STRICT_KTL_XML:
            raise
        msg = "XML setup for orphan keyword {0} failed: {1}".format(name, str(e))
        emit_xml_warning(service.log, msg)
        cls = DFW.Keyword.Keyword
    
    try:
        cls(name=name, service=service)
    except WrongDispatcher:
        service.log.debug("Skipping orphaned keyword {0}, wrong dispatcher.".format(name))
    else:
        msg = "Set up an orphaned keyword {0} for service {1} dispatcher {2}".format(
            name, service.name, service.dispatcher
        )
        emit_xml_warning(service.log, msg)

@xml("KTLXML failed to find units for {self.name:s}. Exception was {exc!s}.")
def get_units_xml(xml, name):
    """Get the keyword's units value from the XML configuration."""
    keyword_xml = xml[name]
    
    units = None
    
    try:
        units = ktlxml.getValue(keyword_xml, 'units')
    except ValueError:
        pass
    
    return units

def emit_xml_warning(log, msg, exc_info=True):
    """Emit an XML error or warning."""
    if WARN_KTL_XML:
        if WARNINGS_KTL:
            warnings.warn(CauldronXMLWarning(msg))
        else:
            log.warning(msg, exc_info=exc_info)