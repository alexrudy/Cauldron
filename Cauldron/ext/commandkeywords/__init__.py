# -*- coding: utf-8 -*-
"""
An extension for a command-based keyword.
"""
from __future__ import absolute_import

from Cauldron.types import Boolean, DispatcherKeywordType
from Cauldron.exc import NoWriteNecessary
from Cauldron.utils.callbacks import Callbacks

class CommandKeyword(Boolean, DispatcherKeywordType):
    """This keyword will receive boolean writes as 1, and will always be set to 0. 
        
        Actions can then be performed in callbacks, etc., every time this keyword is triggered.
    """
    
    KTL_REGISTERED = False
    
    KTL_TYPE = 'boolean'
    
    def __init__(self, *args, **kwargs):
        kwargs['initial'] = '0'
        super(CommandKeyword, self).__init__(*args, **kwargs)
        self._cbs = Callbacks()
    
    def command(self, func):
        """Add command items."""
        self._cbs.add(func)
    
    def prewrite(self, value):
        """Before writing, trigger no-write-necssary if value is False"""
        if self.translate(value) == '0':
            raise NoWriteNecessary("No write needed, command not triggered.")
        return super(CommandKeyword, self).prewrite(value)
    
    def write(self, value):
        """Write to the commands."""
        if str(value) == '1':
            self._cbs(self)
    
    def postwrite(self, value):
        """Special postwrite that always sets the value to '0'."""
        self.set('0', force=True)
    
    # We don't have to do anything else here.
        