# -*- coding: utf-8 -*-
"""
A useful subclass of logger for more fine-grained messaging.
"""

import logging
import weakref

__all__ = ['KeywordMessageFilter']

class Logger(logging.getLoggerClass()):
    """A basic subclass of logger with some useful items."""
    
    def getChild(self, suffix):
        """Get a child logger."""
        return logging.getLogger("{0}.{1}".format(self.name, suffix))
    
    def msg(self, msg, *args, **kwargs):
        """Messaging-level logging."""
        if self.isEnabledFor(5):
            self._log(5, msg, args, **kwargs)
        
    def trace(self, msg, *args, **kwargs):
        """Trace-level logging."""
        if self.isEnabledFor(1):
            self._log(1, msg, args, **kwargs)
        
    
logging.setLoggerClass(Logger)

class KeywordMessageFilter(logging.Filter):
    
    def __init__(self, keyword):
        """Filter using a keyword."""
        logging.Filter.__init__(self)
        self._keyword_name = keyword.full_name
        self._keyword = weakref.ref(keyword)
    
    def filter(self, record):
        """Filter"""
        record.keyword_name = self._keyword_name
        keyword = self._keyword()
        if keyword is not None:
            record.keyword = repr(keyword)
        else:
            record.keyword = "<MissingKeyword '{0}'>".format(self._keyword_name)
        return True
    
    