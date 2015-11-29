#!/usr/bin/env python
# -*- coding: utf-8 -*-

import zmq
ctx = zmq.Context()
ctx.destroy()
print(".destroy() done.")