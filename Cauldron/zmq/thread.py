# -*- coding: utf-8 -*-

import weakref
import logging
import threading
import six
import sys
import collections

from ..config import get_timeout, get_configuration
from ..exc import TimeoutError

try:
    import zmq
except ImportError:
    pass
    

__all__ = ['ZMQThreadError', 'ZMQThread']

class ZMQThreadError(Exception):
    """Child exception"""
    def __init__(self, msg, exc):
        super(ZMQThreadError, self).__init__()
        self.msg = msg
        self.exc = exc
        
    def __str__(self):
        """String representation of the ZMQThreadError"""
        s = "{0!s}".format(self.msg)
        if self.exc is not None:
            s += " from {0!r}".format(self.exc)
        return s

class ZMQThread(threading.Thread, object):
    """A ZMQ Thread control object."""
    def __init__(self, name, context=None):
        super(ZMQThread, self).__init__(name=six.text_type(name))
        self.ctx = weakref.proxy(context or zmq.Context.instance())
        self.running = threading.Event()
        self.started = threading.Event()
        self.finished = threading.Event()
        self.log = logging.getLogger(name)
        self._error = None
        self._exc_tb = None
        self._signal_address = "inproc://signal-{0:s}-{1:s}".format(hex(id(self)), name)
        
    def start(self):
        """Start the thread."""
        self.running.set()
        super(ZMQThread, self).start()
        
    def __del__(self):
        """Clear the running variable."""
        self.running.clear()
        
    def connect(self, socket, address, method='connect'):
        """Connect to the address."""
        try:
            getattr(socket, method)(address)
        except zmq.ZMQError as e:
            self.log.error("{0} can't {1} to address '{1}' because {2}".format(self, method, address, e))
            self._error = e
            self._exc_tb = sys.exc_info()[2]
            raise
        else:
            self.log.trace("{0} {1} to address '{2}'".format(self, method, address))
        return
        
    def get_signal_socket(self):
        """Create and return the signal socket for the thread."""
        signal = self.ctx.socket(zmq.PULL)
        self.connect(signal, self._signal_address, 'bind')
        return signal
        
    def send_signal(self, message=b"", timeout=100):
        """Get a socket to signal to the underlying thread."""
        signal = self.ctx.socket(zmq.PUSH)
        try:
            signal.connect(self._signal_address)
            if signal.poll(timeout=timeout, flags=zmq.POLLOUT):
                try:
                    signal.send(message, flags=zmq.NOBLOCK)
                except zmq.Again as exc: # pragma: no cover
                    self.log.debug("Signalling may have failed, socket would block. finished = {0}".format(self.finished.is_set()))
            elif not self.finished.is_set(): # pragma: no cover
                # We might have missed something.
                self.log.debug("Signalling may have failed. finished = {0} but socket wasn't ready.".format(self.finished.is_set()))
        finally:
            signal.close(linger=10)
            self.log.trace("{0} sent wakeup signal.".format(self))
        
    def run(self):
        """Run the thread."""
        try:
            self.log.trace("{0} starting".format(self))
            self.thread_target()
        except (zmq.ContextTerminated, zmq.ZMQError) as exc: # pragma: no cover
            self.log.debug("{0} ZMQ shutdown because '{1!r}'.".format(self, exc))
            self._error = exc
        except Exception as exc:
            self.log.trace("{0} shutdown because '{1!r}'.".format(self, exc))
            self._error = exc
            self._exc_tb = sys.exc_info()[2]
            self.log.exception("{0} error:".format(self))
            # raise
        else:
            self.log.log(5, "{0} shutdown cleanly.".format(self))
        finally:
            self.finished.set()
            self.started.set()
            self.running.clear()
            self.log.log(5, "{0} finished.".format(self))
        
    def check(self, timeout=1.0):
        """Check that the thread is actually alive."""
        if not self.finished.is_set():
            self.started.wait(timeout)
        if self.finished.is_set() or (not self.started.is_set()):
            msg = "{0} is not alive.".format(self)
            if self._error is not None:
                msg += " Thread Error: {0}".format(repr(self._error))
            else:
                msg += " No error was reported."
            six.reraise(ZMQThreadError, ZMQThreadError(msg, self._error), self._exc_tb)
        
    def signal_stop(self):
        """Signal to the underlying thread in a safe way."""
        if not self.isAlive():
            return
        
        self.log.trace("{0} clearing .running event.".format(self))
        self.running.clear()
        
        # If the thread is starting, wait
        if not self.finished.is_set():
            if not self.started.is_set():
                self.log.trace("{0} waiting for .started event.".format(self))
            self.started.wait()
            
            if self.isAlive() and self.started.is_set():
                self.send_signal()
        
    def stop(self, join=True, timeout=None):
        """Stop the responder thread."""
        # If the thread is not alive, do nothing.
        self.signal_stop()
        
        if join:
            timeout = get_timeout(timeout)
            self.log.trace("{0} joining. timeout={1}".format(self, timeout))
            if self.is_alive():
                self.join(timeout=timeout)
            if not self.is_alive():
                self.log.debug("{0} joined.".format(self))
            else:
                msg = "{0} join timed out.".format(self)
                if get_configuration().getboolean("zmq","error-on-join-timeout"):
                    raise TimeoutError(msg)
                self.log.warning(msg)
        else:
            self.log.debug("{0} stopped.".format(self))