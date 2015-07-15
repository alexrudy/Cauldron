# -*- coding: utf-8 -*-
"""
Declarative allows you to place keyword attributes on instances, and have those instances manage the keyword value.
"""

from .descriptor import KeywordDescriptor, DescriptorBase

__all__ = ['KeywordDescriptor', 'DescriptorBase']