# -*- coding: utf-8 -*-
"""
A queue to handle ZMQ messages asynchronously from the client.
"""

from six.moves import queue
import threading
import time
import zmq
from .common import zmq_connect_socket
from .microservice import ZMQCauldronMessage
from ..utils.callbacks import WeakMethod
from ..exc import TimeoutError
from ..config import get_configuration, get_timeout
from ..base.core import Task as _BaseTask

class Task(_BaseTask):
    """A task container for the task queue."""
    
    def __call__(self, message):
        """Handle this message."""
        try:
            self.result = self.callback(message)
        except Exception as e:
            self.error = e
        finally:
            self.event.set()
        
    

class TaskQueue(threading.Thread):
    """A client task queue"""
    def __init__(self, name, ctx=None, log=None, timeout=None):
        super(TaskQueue, self).__init__(name="Task Queue for {0:s}".format(name))
        self._pending = {}
        self._task_timeout = (get_timeout(timeout) * 1e3) * 1e3 # Wait 1000x the normal timeout, then clear old stuff.
        self.ctx = ctx or zmq.Context.instance()
        self.frontend_address = "inproc://{0:s}-frontend".format(hex(id(self)))
        self.signal_address = "inproc://{0:s}-signal".format(hex(id(self)))
        self.log = log or logging.getLogger("ktl.zmq.TaskQueue.{0:s}".format(name))
        self.daemon = True
        self.shutdown = threading.Event()
        self._local = threading.local()
        
    def _check_timeout(self):
        """Check timeouts for tasks."""
        now = time.time()
        timeout = self._task_timeout
        for starttime, task in list(self._pending.values()):
            if task.timeout is None:
                if (starttime + self._task_timeout) < now:
                    self.log.debug("Task {0} took way too long. Orphaning.".format())
                    task.timedout("Orphaned task stuck in queue.")
                    self._pending.pop(task.identifier)
                continue
            dur = starttime + task.timeout
            if dur < now:
                task.timedout()
                self._pending.pop(task.identifier)
            elif (timeout > (task.timeout * 1e3)):
                timeout = task.timeout * 1e3
        return timeout
        
    @property
    def frontend(self):
        """Retrieve the thread-local frontend socket."""
        if hasattr(self._local, 'frontend'):
            return self._local.frontend
        
        frontend = self.ctx.socket(zmq.PUSH)
        frontend.connect(self.frontend_address)
        self._local.frontend = frontend
        return frontend
        
        
    def put(self, task):
        """Add a task to the queue."""
        self._pending[task.request.identifier] = (time.time(), task)
        self.frontend.send(task.request.identifier)
        
    def run(self):
        """Run the task queue thread."""
        backend = self.ctx.socket(zmq.DEALER)
        zmq_connect_socket(backend, get_configuration(), "broker", log=self.log, label='client')
        
        frontend = self.ctx.socket(zmq.PULL)
        frontend.bind(self.frontend_address)
        
        signal = self.ctx.socket(zmq.PULL)
        signal.bind(self.signal_address)
        
        poller = zmq.Poller()
        poller.register(backend, zmq.POLLIN)
        poller.register(frontend, zmq.POLLIN)
        poller.register(signal, zmq.POLLIN)
        
        timeout = self._check_timeout()
        
        while not self.shutdown.isSet():
            ready = dict(poller.poll(timeout=timeout))
            
            # We got a signal!
            if signal in ready:
                _ = signal.recv()
                continue
            
            # We can recieve something!
            if backend in ready:
                try:
                    message = ZMQCauldronMessage.parse(backend.recv_multipart())
                except Exception as e:
                    # un-parseable message, discard it.
                    self.log.exception("Discarding {0}".format(str(e)))
                else:
                    starttime, task = self._pending.pop(message.identifier)
                    task(message)
                
            # We need to ask for something new.
            if frontend in ready:
                identifier = frontend.recv()
                starttime, task = self._pending.get(identifier)
                backend.send(b"", flags=zmq.SNDMORE)
                backend.send_multipart(task.request.data)
            
            timeout = self._check_timeout()
            
        
    def stop(self):
        """Stop the task-queue thread."""
        self.shutdown.set()
        signal = self.ctx.socket(zmq.PUSH)
        signal.connect(self.signal_address)
        signal.send(b"SENTINEL")
        signal.close()
        self.join()