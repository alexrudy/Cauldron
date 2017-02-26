# -*- coding: utf-8 -*-
"""
An extension for a heartbeat keyword following the convention used by KTL in the wild
"""
from __future__ import absolute_import

from Cauldron.types import Integer, DispatcherKeywordType
from Cauldron.exc import NoWriteNecessary
from Cauldron.utils.callbacks import Callbacks

__all__ = ['HeartbeatKeyword']

class HeartbeatKeyword(Integer, DispatcherKeywordType):
    """This keyword will update with a period to identify a dispatcher as alive.
    """
    
    KTL_REGISTERED = False
    
    KTL_TYPE = 'integer'
    
    def __init__(self, *args, **kwargs):
        kwargs['initial'] = '0'
        kwargs['period']  = 1
        super(HeartbeatKeyword, self).__init__(*args, **kwargs)
    
    def read(self):
        """Read this keyword"""
        self.increment()
        return self.value
    
    # We don't have to do anything else here.
        