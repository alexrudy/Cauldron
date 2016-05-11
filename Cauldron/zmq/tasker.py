# -*- coding: utf-8 -*-
"""
A queue to handle ZMQ messages asynchronously from the client.
"""

from six.moves import queue
import threading
import time
from .common import zmq_connect_socket, check_zmq
from .protocol import ZMQCauldronMessage
from .microservice import ZMQThread
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
        
    

class TaskQueue(ZMQThread):
    """A client task queue"""
    def __init__(self, name, ctx=None, log=None, timeout=None):
        super(TaskQueue, self).__init__(name="ktl.Service.{0:s}.Tasks".format(name), context=ctx)
        zmq = check_zmq()
        self._pending = {}
        self._task_timeout = ((get_timeout(timeout) or 1.0) * 60) # Wait 60x the normal timeout, then clear old stuff.
        self.frontend_address = "inproc://{0:s}-frontend".format(hex(id(self)))
        self.daemon = True
        self._local = threading.local()
        self._frontend_sockets = []
        
    def _check_timeout(self):
        """Check timeouts for tasks."""
        now = time.time()
        timeout = 5.0
        for starttime, task in list(self._pending.values()):
            if task.timeout is None:
                if (starttime + self._task_timeout) < now:
                    self.log.debug("Task {0} took way too long. Orphaning.".format(task))
                    task.timedout("Orphaned task stuck in queue.")
                    self._pending.pop(task.request.identifier)
                continue
            dur = starttime + task.timeout
            if dur < now:
                self.log.debug("{0!r}.timeout({1})".format(self, task.request))
                task.timedout()
                self._pending.pop(task.request.identifier)
            elif (timeout > (task.timeout * 1e3)):
                timeout = task.timeout * 1e3
        return timeout
        
    @property
    def frontend(self):
        """Retrieve the thread-local frontend socket."""
        zmq = check_zmq()
        if hasattr(self._local, 'frontend'):
            return self._local.frontend
        
        frontend = self.ctx.socket(zmq.PUSH)
        frontend.connect(self.frontend_address)
        self._local.frontend = frontend
        self._frontend_sockets.append(frontend)
        return frontend
        
    def __del__(self):
        """When deleting this object, make sure all of the sockets are closed."""
        for socket in self._frontend_sockets:
            socket.close()
        
    def put(self, task):
        """Add a task to the queue."""
        self._pending[task.request.identifier] = (time.time(), task)
        self.frontend.send(task.request.identifier)
        
    def run(self):
        """Run the thread."""
        import zmq
        try:
            self.starting.set()
            self.log.debug("{0} starting".format(self))
            self.respond()
        except (zmq.ContextTerminated, zmq.ZMQError) as e:
            self.log.log(5, "TaskQueue shutdown because '{0!r}'.".format(e))
            self._error = e
        except Exception as e:
            self._error = e
            self.log.log(5, "TaskQueue shutdown because '{0!r}'.".format(e))
            raise
        else:
            self.log.log(5, "Shutting down the TaskQueue cleanly.")
        finally:
            self.log.log(5, "TaskQueue thread finished.")
            self.running.clear()
            self.starting.clear()
        
    def respond(self):
        """Run the task queue thread."""
        zmq = check_zmq()
        backend = self.ctx.socket(zmq.DEALER)
        zmq_connect_socket(backend, get_configuration(), "broker", log=self.log, label='client')
        
        frontend = self.ctx.socket(zmq.PULL)
        frontend.bind(self.frontend_address)
        
        signal = self.get_signal_socket()
        
        poller = zmq.Poller()
        poller.register(backend, zmq.POLLIN)
        poller.register(frontend, zmq.POLLIN)
        poller.register(signal, zmq.POLLIN)
        
        timeout = self._check_timeout()
        
        self.running.set()
        self.starting.clear()
        while self.running.is_set():
            ready = dict(poller.poll(timeout=timeout))
            
            # We got a signal!
            if signal in ready:
                _ = signal.recv()
                continue
            
            # We can recieve something!
            if backend in ready:
                try:
                    message = ZMQCauldronMessage.parse(backend.recv_multipart())
                    self.log.debug("{0!r}.recv({1})".format(self, message))
                except Exception as e:
                    # un-parseable message, discard it.
                    self.log.exception("Discarding {0}".format(str(e)))
                else:
                    try:
                        starttime, task = self._pending.pop(message.identifier)
                    except KeyError:
                        # This task had probably timed out.
                        self.log.debug("{0!r}.recv({1}) missing".format(self, message))
                    else:
                        task(message)
                
            # We need to ask for something new.
            if frontend in ready:
                identifier = frontend.recv()
                starttime, task = self._pending[identifier]
                self.log.debug("{0!r}.send({1})".format(self, task.request))
                backend.send(b"", flags=zmq.SNDMORE)
                backend.send_multipart(task.request.data)
            
            timeout = self._check_timeout()
            
        backend.close()
        frontend.close()
        signal.close()
        self.log.debug("{0!r} done.".format(self))
        
