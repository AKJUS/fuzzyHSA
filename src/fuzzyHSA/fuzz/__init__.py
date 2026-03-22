# SPDX-License-Identifier: Apache-2.0
"""Fuzzing framework for KFD/GPU testing."""

from .types import FuzzCase, FuzzResult, FuzzStatus, FuzzStats
from .mutators import (
    Mutator,
    BitflipMutator,
    ByteflipMutator,
    BoundaryMutator,
    ArithmeticMutator,
    ZeroMutator,
    CompositeMutator,
)
from .harness import FuzzHarness, HarnessConfig
from .targets import FuzzTarget, IoctlTarget

__all__ = [
    # Types
    "FuzzCase",
    "FuzzResult",
    "FuzzStatus",
    "FuzzStats",
    # Mutators
    "Mutator",
    "BitflipMutator",
    "ByteflipMutator",
    "BoundaryMutator",
    "ArithmeticMutator",
    "ZeroMutator",
    "CompositeMutator",
    # Harness
    "FuzzHarness",
    "HarnessConfig",
    # Targets
    "FuzzTarget",
    "IoctlTarget",
]
