# -*- coding: utf-8 -*-
"""
An extension for a command-based keyword.
"""
from __future__ import absolute_import

from Cauldron.types import Boolean, dispatcher_keyword
from Cauldron.exc import NoWriteNecessary

@dispatcher_keyword
class CommandKeyword(Boolean):
    """This keyword will recieve boolean writes as 1, and will always be set to 0. 
        
        Actions can then be performed in callbacks, etc., every time this keyword is triggered.
    """
    
    def __init__(self, *args, **kwargs):
        kwargs['initial'] = '0'
        super(CommandKeyword, self).__init__(*args, **kwargs)
    
    def prewrite(self, value):
        """Before writing, trigger no-write-necssary if value is False"""
        if self.translate(value) == '0':
            raise NoWriteNecessary("No write needed, command not triggerd.")
        return super(CommandKeyword, self).prewrite(value)
    
    def postwrite(self, value):
        """Special postwrite that always sets the value to '0'."""
        self.set('0', force=True)
    
    # We don't have to do anything else here.
        