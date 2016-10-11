# -*- coding: utf-8 -*-

import weakref
import logging
import threading
import six
import collections

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

class ZMQThread(threading.Thread):
    """A ZMQ Thread control object."""
    def __init__(self, name, context=None):
        super(ZMQThread, self).__init__(name=six.text_type(name))
        self.ctx = weakref.proxy(context or zmq.Context.instance())
        self.running = threading.Event()
        self.started = threading.Event()
        self.finished = threading.Event()
        self.log = logging.getLogger(name)
        self._error = None
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
            raise
        else:
            self.log.debug("{0} {1} to address '{2}'".format(self, method, address))
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
            self.log.debug("{0} sending wakeup signal.".format(self))
            signal.connect(self._signal_address)
            if signal.poll(timeout=timeout, flags=zmq.POLLOUT):
                try:
                    signal.send(message, flags=zmq.NOBLOCK)
                except zmq.Again as exc: # pragma: no cover
                    self.log.debug("Signalling may have failed, socket would block. finished = {0}".format(self.finished.is_set()))
                    pass
            elif not self.finished.is_set(): # pragma: no cover
                # We might have missed something.
                self.log.debug("Signalling may have failed. finished = {0} but socket wasn't ready.".format(self.finished.is_set()))
        finally:
            signal.close(linger=10)
            self.log.debug("{0} sent wakeup signal.".format(self))
        
    def run(self):
        """Run the thread."""
        try:
            self.log.debug("[{0}] starting".format(self.name))
            self.thread_target()
        except (zmq.ContextTerminated, zmq.ZMQError) as exc: # pragma: no cover
            self.log.log(5, "[{0}] ZMQ shutdown because '{1!r}'.".format(self.name, exc))
            self._error = exc
        except Exception as exc:
            self.log.log(5, "[{0}] shutdown because '{1!r}'.".format(self.name, exc))
            self._error = exc
            self.log.exception("[{0}] error:".format(self.name))
            # raise
        else:
            self.log.log(5, "[{0}] shutdown cleanly.".format(self.name))
        finally:
            self.finished.set()
            self.started.set()
            self.running.clear()
            self.log.log(5, "[{0}] finished.".format(self.name))
        
    def check(self, timeout=1.0):
        """Check that the thread is actually alive."""
        if not self.finished.is_set():
            self.running.wait(timeout)
        if self.finished.is_set() or (not self.running.is_set()):
            msg = "[{0}] is not alive.".format(self.name)
            if self._error is not None:
                msg += " Thread Error: {0}".format(repr(self._error))
            else:
                msg += " No error was reported."
            raise ZMQThreadError(msg, self._error)
        
    def stop(self, join=False, timeout=None):
        """Stop the responder thread."""
        # If the thread is not alive, do nothing.
        if not self.isAlive():
            return
        
        self.log.debug("{0} clearing .running event.".format(self))
        self.running.clear()
        
        # If the thread is starting, wait
        if not self.finished.is_set():
            self.log.debug("{0} waiting for .started event.".format(self))
            self.started.wait()
            
            if self.isAlive() and self.started.is_set():
                self.send_signal()
                
        
        if join or (not self.daemon):
            self.log.debug("{0} joining.".format(self))
            self.join(timeout=timeout)
            self.log.debug("{0} joined.".format(self))
            
        self.log.debug("{0} stopped.".format(self.name))