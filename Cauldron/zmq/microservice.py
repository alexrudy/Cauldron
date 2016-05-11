# -*- coding: utf-8 -*-
"""
A simple microservice framework for ZMQ Messaging.
"""

import weakref
import logging
import threading
import six
import binascii
import collections
import uuid

from ..exc import DispatcherError
from .protocol import ZMQCauldronErrorResponse
from .thread import ZMQThread, ZMQThreadError

FRAMEBLANK = six.binary_type(b"\x01")
FRAMEFAIL = six.binary_type(b"\x02")
FRAMEDELIMITER = six.binary_type(b"")

__all__ = ['ZMQMicroservice', 'FRAMEBLANK', 'FRAMEFAIL', 'FRAMEDELIMITER']

class ZMQMicroservice(ZMQThread):
    """A ZMQ Responder tool."""
    
    def __init__(self, context, address, name="microservice", timeout=5):
        super(ZMQMicroservice, self).__init__(name=six.text_type(name), context=context)
        self.timeout = float(timeout)
        self.address = address
        
    def check(self, timeout=0.1):
        """Check for errors."""
        try:
            super(ZMQMicroservice, self).check(timeout)
        except ZMQThreadError as exc:
            raise DispatcherError(exc.msg)
        
        
    def main(self):
        """Main function should call respond."""
        self.respond()
        
    def handle(self, message):
        """Handle a message, raising an error if appropriate."""
        try:
            method_name = "handle_{0:s}".format(message.command)
            if not hasattr(self, method_name):
                message.raise_error_response("Bad command '{0:s}'!".format(message.command))
            response_payload = getattr(self, method_name)(message)
        except ZMQCauldronErrorResponse as e:
            return e.message
        except Exception as e:
            self.log.exception("Error handling '{0}': {1!r}".format(message.command, e))
            return message.error_response("{0!r}".format(e))
        else:
            response = message.response(response_payload)
            return response
    
    
        