"""
This package implements a wrapper for ADPAC which does not require modifying
ADPAC itself.  All manipulations are performed by reading/writing input/output
files.  This is typically sufficient for loose coupling between other
components and an ADPAC simulation.
"""

from __future__ import absolute_import

from .wrapper import ADPAC, ProbeRequest

