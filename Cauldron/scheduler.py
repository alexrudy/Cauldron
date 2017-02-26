# -*- coding: utf-8 -*-
"""
Generic interface to scheduling keyword updates for KTL
"""
# -*- coding: utf-8 -*-
import collections
import threading
import heapq
import time
import weakref
import logging
import datetime
import six

from .base.core import _CauldronBaseMeta

now = time.time
log = logging.getLogger(__name__)

Appointment = collections.namedtuple("Appointment", ["next_event", "keywords"])

_keyword_update_errors = collections.defaultdict(lambda : 0)
MAX_KEYWORD_UPDATE_ERRORS = 5

def _keyword_update(keyword_ref):
    """Run the keyword update command."""
    keyword = keyword_ref()
    if keyword is None:
        return False
    try:
        with keyword._lock:
            value = keyword.update()
    except Exception as e:
        keyword.log.exception("Exception during periodic update of {0!r}".format(e))
        _keyword_update_errors[keyword.full_name] += 1
        if _keyword_update_errors[keyword.full_name] > MAX_KEYWORD_UPDATE_ERRORS:
            keyword.log.exception("More than {0:d} exceptions for {1:s}, canceling updates.".format(MAX_KEYWORD_UPDATE_ERRORS, keyword.full_name))
            return False
    return True

class Collection(object):
    """A periodic collection"""
    def __init__(self, period):
        super(Collection, self).__init__()
        self.period = period
        self.next_event = _normalize_time(now() + self.period)
        self.keywords = []
        self._lock = threading.RLock()
        
    def __len__(self):
        """Number of keywords in the collection."""
        with self._lock:
            return len(self.keywords)
        
    def append(self, keyword):
        """Add a keyword."""
        with self._lock:
            self.keywords.append(keyword)
        
    def update(self):
        """Update the keywords."""
        with self._lock:
            to_remove = []
            next_update = now() + self.period
            for keyword in self.keywords:
                log.log(5, "Updating {0!r}".format(keyword))
                alive = _keyword_update(keyword)
                if not alive:
                    to_remove.append(keyword)
            for keyword in to_remove:
                self.keywords.remove(keyword)
            finished = now()
            if next_update <= finished:
                log.log(5, "Update took too long, increasing waiting period.")
                n = ((finished - next_update) // self.period) + 1
                next_update = finished + (self.period * n)
            self.next_event = _normalize_time(next_update)

class TimingDictionary(object):
    """A dictionary of timing items."""
    def __init__(self):
        super(TimingDictionary, self).__init__()
        self.__data = dict()
        self.__heap = list()
        self.locked = threading.RLock()
        
    @property
    def next_event(self):
        """Get the next time."""
        with self.locked:
            if len(self.__heap):
                return time.mktime(self.__heap[0][0].timetuple())
            else:
                return float('+inf')
        
    def __len__(self):
        """Length"""
        return len(self.__heap)
        
    def __contains__(self, key):
        """See if a key is in the data"""
        return self.__data.__contains__(key)
        
    def push(self, key, value):
        """Add a time item."""
        if key not in self.__data:
            heapq.heappush(self.__heap, (value.next_event, key))
        self.__data[key] = value
    
    def __getitem__(self, key):
        """Get a time item"""
        return self.__data[key]
    
    def remove(self, key):
        """Delete an item."""
        with self.locked:
            value = self.__data.pop(key)
            heap = []
            for _next, _key in self.__heap:
                if _key != key:
                    heapq.heappush(heap, (_next, key))
            self.__heap = heap
    
    def pop(self):
        """Pop the next time off the queue."""
        _, key = heapq.heappop(self.__heap)
        return self.__data.pop(key)

def _normalize_time(time):
    """Normalize a time, truncating to seconds."""
    if hasattr(time, 'year'):
        # Truncate microseconds from appoitment times
        return datetime.datetime(time.year, time.month, time.day, time.hour, time.minute, time.second)
    else:
        return datetime.datetime.fromtimestamp(round(float(time), 0))

@six.add_metaclass(_CauldronBaseMeta)
class Scheduler(object):
    """A scheduler maintains appointments and periods, and responds with the next timeout."""
    def __init__(self, *args, **kwargs):
        super(Scheduler, self).__init__(*args, **kwargs)
        self._appointments = TimingDictionary()
        self._periods = TimingDictionary()
        
    def appointment(self, time, keyword):
        """An appointment at a given time, with a given callback."""
        dt = _normalize_time(time)
        with self._appointments.locked:
            try:
                appointment = self._appointments[dt]
            except KeyError:
                appointment = Appointment(dt, [weakref.ref(keyword)])
                self._appointments.push(dt, appointment)
            else:
                appointment.keywords.append(weakref.ref(keyword))
            self.wake()
        
    def cancel_appointment(self, time, keyword):
        """Cancel the appointment."""
        dt = _normalize_time(time)
        with self._appointments.locked:
            try:
                appointment = self._appointments[dt]
            except KeyError: # pragma: no cover
                log.warn("Appointment at {0!r} for keyword {1!r} has already been canceled.".format(time, keyword))
            else:
                appointment.keywords.remove(weakref.ref(keyword))
                if not len(appointment.keywords):
                    self._appointments.remove(dt)
            self.wake()
        
    def period(self, interval, keyword):
        """Set a keyword to be updated with an interval."""
        interval = round(float(interval), 1)
        interval = max([interval, 0.1])
        with self._periods.locked:
            try:
                collection = self._periods[interval]
            except KeyError:
                collection = Collection(interval)
                self._periods.push(interval, collection)
            collection.append(weakref.ref(keyword))
            self.wake()
        
    def get_timeout(self):
        """Get the timeout interval which waits until the next iteration is ready."""
        timeout = min([self._periods.next_event, self._appointments.next_event]) - now()
        if timeout < 0.1:
            timeout = 0.1
        if timeout > 300.0:
            timeout = 300.0
        return timeout
    
    def run_periods(self, at=None):
        """Run period-triggered keywords."""
        at = at or now()
        if len(self._periods) and self._periods.next_event <= at:
            with self._periods.locked:
                collection = self._periods.pop()
                collection.update()
                if len(collection):
                    self._periods.push(collection.period, collection)
    
    def run_appointments(self, at=None):
        """Run appointments-triggered keywords."""
        at = at or now()
        if len(self._appointments) and self._appointments.next_event <= at:
            with self._appointments.locked:
                appointment = self._appointments.pop()
            for keyword in appointment.keywords:
                _keyword_update(keyword)
        

                