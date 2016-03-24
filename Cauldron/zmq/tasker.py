# -*- coding: utf-8 -*-
"""
A queue to handle ZMQ messages asynchronously from the client.
"""

from six.moves import queue
import threading
import zmq
from .common import zmq_connect_socket
from .microservice import ZMQCauldronMessage
from ..utils.callbacks import WeakMethod
from ..exc import TimeoutError
from ..config import get_configuration, get_timeout

class Task(object):
    """A task container for the task queue."""
    
    __slots__ = ('request', 'event', 'result', 'response', 'error', 'callback', 'timeout')
    
    def __init__(self, message, callback, timeout=None):
        super(Task, self).__init__()
        self.request = message
        self.timeout = timeout
        self.callback = WeakMethod(callback)
        self.response = None
        self.result = None
        self.error = None
        self.event = threading.Event()
        
    def __call__(self, socket):
        """Handle this message."""
        socket.send_multipart(self.request.data)
        
        if self.timeout:
            if not socket.poll(self.timeout * 1e3):
                self.error = TimeoutError("Dispatcher timed out.")
                self.event.set()
                return
        try:
            self.result = self.callback(ZMQCauldronMessage.parse(socket.recv_multipart()))
        except Exception as e:
            self.error = e
        self.event.set()
        
    def wait(self, timeout=None):
        """Wait for this task to be finished."""
        self.event.wait(timeout=get_timeout(timeout))
        return self.event.isSet()
    
    def get(self, timeout=None):
        """Get the result."""
        if not self.wait(timeout=timeout):
            raise TimeoutError("Task timed out.")
        elif self.error is not None:
            raise self.error
        return self.result

class TaskQueue(threading.Thread):
    """A client task queue"""
    def __init__(self, name, ctx=None, log=None):
        super(TaskQueue, self).__init__(name="Task Queue for {0:s}".format(name))
        self.queue = queue.Queue()
        self.ctx = ctx or zmq.Context.instance()
        self.log = log or logging.getLogger("ktl.zmq.TaskQueue.{0:s}".format(name))
        self.daemon = True
        self.shutdown = threading.Event()
        
    def run(self):
        """Run the task queue thread."""
        socket = self.ctx.socket(zmq.REQ)
        zmq_connect_socket(socket, get_configuration(), "broker", log=self.log, label='client')
        while not self.shutdown.isSet():
            try:
                task = self.queue.get()
                if task is None:
                    raise queue.Empty
                self.log.log(5, "{0!r}.send({1!s})".format(self, task.request))
                task(socket)
                self.queue.task_done()
            except queue.Empty:
                pass
        
    def stop(self):
        """Stop the task-queue thread."""
        self.shutdown.set()
        try:
            self.queue.put(None, block=False)
        except queue.Full:
            pass
        self.join()