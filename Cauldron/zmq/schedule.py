# -*- coding: utf-8 -*-
import collections
import threading
import heapq
import time
import weakref
import logging
import datetime

from .common import check_zmq
from .thread import ZMQThread
from ..scheduler import Scheduler

__all__ = ['ZMQScheduler']

now = time.time()

class ZMQScheduler(ZMQThread, Scheduler):
    """A scheduler maintains appointments and periods, and responds with the next timeout."""
    def __init__(self, name="Scheduler", context=None):
        super(ZMQScheduler, self).__init__(name=name, context=context)
        Scheduler.__init__(self)
        
    def wake(self):
        """Wake up the thread."""
        self.send_signal()
    
    def thread_target(self):
        """Run the thread."""
        signal = self.get_signal_socket()
        
        self.started.set()
        try:
            while self.running.isSet():
                timeout = self.get_timeout()
                if signal.poll(timeout=timeout * 1e3):
                    _ = signal.recv()
                    self.log.log(5, "Got a signal: .running = {0}".format(self.running.is_set()))
                    continue
                
                thetime = now()
                self.run_periods(at=thetime)
                self.run_appointments(at=thetime)
        finally:
            signal.close(linger=0)
                