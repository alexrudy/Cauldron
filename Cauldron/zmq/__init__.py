# -*- coding: utf-8 -*-
"""
ZeroMQ is a networking protocol with socket-like objects
for writing highly distributed apps. Here, it is used to
implement the request-reply pattern for keyword passing
interfaces, including error handling responses.

"""
from .common import ZMQ_AVAILABLE

from . import client
from . import dispatcher


