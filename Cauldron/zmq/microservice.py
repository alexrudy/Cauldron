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

FRAMEBLANK = six.binary_type(b"\x01")
FRAMEFAIL = six.binary_type(b"\x02")
FRAMEDELIMITER = six.binary_type(b"")

class ZMQThread(threading.Thread):
    """A ZMQ Thread control object."""
    def __init__(self, name, context=None):
        super(ZMQThread, self).__init__(name=six.text_type(name))
        import zmq
        self.ctx = weakref.proxy(context or zmq.Context.instance())
        self.running = threading.Event()
        self.starting = threading.Event()
        self.log = logging.getLogger(name)
        self._error = None
        self._signal_address = "inproc://signal-{0:s}-{1:s}".format(hex(id(self)), name)
        
    def connect(self, socket, address, method='connect'):
        """Connect to the address."""
        import zmq
        try:
            getattr(socket, method)(address)
        except zmq.ZMQError as e:
            self.log.error("{0} can't {1} to address '{1}' because {2}".format(self, method, address, e))
            self._error = e
            raise
        else:
            self.log.debug("{0} {1} to address '{2}'".format(self, method, address))
        return
        
    def get_signal_socket(self):
        """Create and return the signal socket for the thread."""
        import zmq
        signal = self.ctx.socket(zmq.PULL)
        self.connect(signal, self._signal_address, 'bind')
        return signal
        
    def send_signal(self, message=b""):
        """Get a socket to signal to the underlying thread."""
        import zmq
        signal = self.ctx.socket(zmq.PUSH)
        try:
            signal.connect(self._signal_address)
            signal.send(message)
        finally:
            signal.close()
        
    def check(self, timeout=1.0):
        """Check that the thread is actually alive."""
        self.running.wait(timeout)
        if not self.running.is_set():
            msg = "The dispatcher responder thread is not alive."
            if self._error is not None:
                msg += " Thread Error: {0}".format(repr(self._error))
            else:
                msg += " No error was reported."
            raise DispatcherError(msg)
        
    def stop(self, join=False):
        """Stop the responder thread."""
        import zmq
        if not self.isAlive():
            return
        if self.starting.isSet():
            self.running.wait(timeout=0.1)
        self.log.debug("{0} stopping".format(self))
        if self.running.is_set() and (not self.ctx.closed):
            self.running.clear()
            if not self.isAlive():
                return
            self.send_signal()
        self.running.clear()
        if join or (not self.daemon):
            self.join()
        self.log.debug("Stopped microservice {0}".format(self.name))

class ZMQMicroservice(ZMQThread):
    """A ZMQ Responder tool."""
    
    def __init__(self, context, address, name="microservice", timeout=5):
        super(ZMQMicroservice, self).__init__(name=six.text_type(name), context=context)
        self.timeout = float(timeout)
        self.address = address
        
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
    
    def run(self):
        """Run the thread."""
        import zmq
        try:
            self.starting.set()
            self.log.debug("{0} starting".format(self))
            self.respond()
        except (zmq.ContextTerminated, zmq.ZMQError) as e:
            self.log.log(5, "Service shutdown because '{0!r}'.".format(e))
            self._error = e
        except Exception as e:
            self._error = e
            self.log.log(5, "Service shutdown because '{0!r}'.".format(e))
            raise
        else:
            self.log.log(5, "Shutting down the responder cleanly.")
        finally:
            self.log.log(5, "Respoder thread finished.")
        
        