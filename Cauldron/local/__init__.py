# -*- coding: utf-8 -*-

# Ensure that imports trigger.
def setup_local_backend():
    """Set up the local backend."""
    from . import client
    from . import dispatcher