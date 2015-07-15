# -*- coding: utf-8 -*-

from .client import Keyword as ClientKeyword, Service as ClientService
from .dispatcher import Keyword as DispatcherKeyword, Service as DispatcherService

__all__ = ['DispatcherKeyword', 'DispatcherService', 'ClientKeyword', 'ClientService']