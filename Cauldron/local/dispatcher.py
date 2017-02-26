# -*- coding: utf-8 -*-
"""
Local dispatcher.

The local interface is process-local. It is lightweight, and good for testing environments, but doesn't handle anything that wouldn't normally be process local.

"""

from ..base import DispatcherService, DispatcherKeyword
from ..scheduler import Scheduler
from ..utils.callbacks import Callbacks
from .. import registry

import time
import weakref
import logging
import threading

__all__ = ['Service', 'Keyword']

_registry = weakref.WeakValueDictionary()

@registry.dispatcher.teardown_for("local")
def clear():
    """Clear the registry."""
    _registry.clear()

class LocalScheduler(Scheduler, threading.Thread):
    """A local scheduling object"""
    
    def __init__(self, name, log=None):
        super(LocalScheduler, self).__init__(name="Scheudler for {0:s}".format(name))
        self.log = log or logging.getLogger("DFW.local.Scheduler.{0:s}".format(name))
        self.shutdown = threading.Event()
        self.waker = threading.Event()
        
    def wake(self):
        """Wake up the thread."""
        self.waker.set()
        
    def run(self):
        """Run the task queue thread."""
        while not self.shutdown.isSet():
            now = time.time()
            self.run_periods(at=thetime)
            self.run_appointments(at=thetime)
            timeout = self.get_timeout()
            self.waker.wait(timeout=timeout)
            self.waker.clear()
        
    def stop(self):
        """Stop the task-queue thread."""
        self.shutdown.set()
        self.waker.set()
        self.join()
        self.log.debug("Closed task queue")
    

@registry.dispatcher.service_for("local")
class Service(DispatcherService):
    
    _scheduler = None
    
    @classmethod
    def get_service(cls, name):
        """Get a dispatcher for a service."""
        #TODO: Support inverse client startup ordering.
        name = str(name).lower()
        return _registry[name]
    
    def __init__(self, name, config, setup=None, dispatcher=None):
        if str(name).lower() in _registry:
            raise ValueError("Cannot have two services with name '{0}' in local registry.".format(name))
        super(Service, self).__init__(name, config, setup, dispatcher)
        
    def _prepare(self):
        self._scheduler = LocalScheduler(self.name)
        
    def _begin(self):
        """Indicate that this service is ready to act, by inserting it into the local registry."""
        _registry[self.name] = self
        self._scheduler.start()
        
    def shutdown(self):
        """To shutdown this service, delete it."""
        if self._scheduler is not None:
            try:
                self._scheduler.stop()
            except Exception:
                pass
                


@registry.dispatcher.keyword_for("local")
class Keyword(DispatcherKeyword):
    
    def __init__(self, name, service, initial=None, period=None):
        super(Keyword, self).__init__(name, service, initial, period)
        self._consumers = Callbacks()
    
    def _broadcast(self, value):
        """Notify consumers that this value has changed."""
        self._consumers(value)
        
    def schedule(self, appointment=None, cancel=False):
        if cancel:
            self.service._scheduler.cancel_appointment(appointment, self)
        else:
            self.service._scheduler.appointment(appointment, self)
    
    def period(self, period):
        self.service._scheduler.period(period, self)
