# SPDX-License-Identifier: Apache-2.0
"""Fuzz targets."""

from .base import FuzzTarget
from .ioctl import IoctlTarget

__all__ = ["FuzzTarget", "IoctlTarget"]
