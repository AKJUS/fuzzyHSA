# SPDX-License-Identifier: Apache-2.0
"""Base protocol for fuzz targets."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import FuzzCase, FuzzResult


class FuzzTarget(ABC):
    """
    Abstract base class for fuzz targets.

    A fuzz target knows how to:
    1. Generate test cases (possibly with mutations)
    2. Execute those cases against the system under test
    3. Determine if the result is interesting (crash, hang, etc.)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this target."""
        ...

    @property
    @abstractmethod
    def operations(self) -> list[str]:
        """List of operations this target can fuzz."""
        ...

    @abstractmethod
    def generate_case(self, seed: int, operation: str | None = None) -> FuzzCase:
        """
        Generate a fuzz case.

        Args:
            seed: Random seed for reproducibility
            operation: Specific operation to target, or None for random

        Returns:
            A FuzzCase ready for execution
        """
        ...

    @abstractmethod
    def execute(self, case: FuzzCase) -> FuzzResult:
        """
        Execute a fuzz case.

        Args:
            case: The case to execute

        Returns:
            FuzzResult with status and any captured output
        """
        ...
