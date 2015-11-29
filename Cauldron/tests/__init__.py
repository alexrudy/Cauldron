# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This packages contains affiliated package tests.
"""

import pytest
pytestmark = [pytest.mark.usefixtures("teardown_cauldron")]


pytestmark.append("router")