# -*- coding: utf-8 -*-
from __future__ import absolute_import

"""
This file contains tools specific to fixing bugs in DFW/ktl when found.
"""

__all__ = ['setupKeywords']


def setupKeywords(self):
    from DFW import Keyword
    from Cauldron.extern import ktlxml
    print("Setting up keywords (bugfixed)")
    pending = []

    for name,value in self._keywords.items ():

        if value != None:
            continue

        xml = self.xml[name]
        type = ktlxml.Get.value (xml, 'type')
        type = type.lower ()

        if type == 'boolean':
            keyword_class = Keyword.Boolean
        elif type == 'double':
            keyword_class = Keyword.Double
        elif type == 'double array':
            keyword_class = Keyword.DoubleArray
        elif type == 'enumerated':
            keyword_class = Keyword.Enumerated
        elif type == 'float':
            keyword_class = Keyword.Float
        elif type == 'float array':
            keyword_class = Keyword.FloatArray
        elif type == 'integer':
            keyword_class = Keyword.Integer
        elif type == 'integer array':
            keyword_class = Keyword.IntegerArray
        elif type == 'mask':
            keyword_class = Keyword.Mask
        elif type == 'string':
            keyword_class = Keyword.String
        else:
            raise ValueError ("unrecognized type '%s' for '%s'" % (type, name))
        
        try:
            keyword_class (name, self)
        except Keyword.WrongDispatcher:
            continue
        
        
        proxy = self.xml.proxy (name)
        
        if proxy != None:
            service,keyword = proxy
            Keyword.proxy (self[name], service, keyword)
                


