# SPDX-License-Identifier: Apache-2.0
"""IOCTL fuzzing target."""

from __future__ import annotations

import random
import time

from ...kfd import KFDDevice, execute_ioctl_raw, get_ioctls, struct_to_bytes
from ..mutators import CompositeMutator
from ..types import FuzzCase, FuzzResult, FuzzStatus
from .base import FuzzTarget

# Operations that modify/destroy state and could corrupt subsequent tests
DANGEROUS_OPERATIONS = frozenset({
    "destroy_queue",
    "destroy_event",
    "free_memory_of_gpu",
    "unmap_memory_from_gpu",
})

# Expected error messages that indicate driver correctly rejected input
EXPECTED_ERRORS = frozenset({
    "Invalid argument",
    "Bad address",
    "Permission denied",
    "No such device",
})


class IoctlTarget(FuzzTarget):
    """
    Fuzz target for KFD ioctl operations.

    Generates valid ioctl structures, mutates them, and executes
    them against the KFD driver.
    """

    def __init__(
        self,
        device: KFDDevice,
        mutator: CompositeMutator | None = None,
        skip_dangerous: bool = True,
    ):
        """
        Initialize ioctl fuzzing target.

        Args:
            device: KFD device to fuzz
            mutator: Mutation strategy (default: composite)
            skip_dangerous: Skip operations that might corrupt state
        """
        self._device = device
        self._mutator = mutator or CompositeMutator()
        self._ioctls = get_ioctls()
        self._skip_dangerous = skip_dangerous
        self._cached_operations: list[str] | None = None

    @property
    def name(self) -> str:
        return "ioctl"

    @property
    def operations(self) -> list[str]:
        """Get list of operations to fuzz (cached)."""
        if self._cached_operations is None:
            all_ops = set(self._ioctls.list_ioctls())
            if self._skip_dangerous:
                self._cached_operations = sorted(all_ops - DANGEROUS_OPERATIONS)
            else:
                self._cached_operations = sorted(all_ops)
        return self._cached_operations

    def generate_case(
        self,
        seed: int,
        operation: str | None = None,
        base_values: dict | None = None,
    ) -> FuzzCase:
        """
        Generate a mutated ioctl fuzz case.

        Args:
            seed: Random seed for reproducibility
            operation: Operation to fuzz (random if None)
            base_values: Optional dict of field_name -> value to set before mutation
        """
        rng = random.Random(seed)

        if operation is None:
            if not self.operations:
                raise ValueError("No operations available to fuzz")
            operation = rng.choice(self.operations)

        ioctl_def = self._ioctls.get_definition(operation)
        if ioctl_def is None:
            raise ValueError(f"Unknown operation: {operation}")

        # Create struct (with base values if provided, otherwise zeroes)
        struct_instance = ioctl_def.struct_type(**(base_values or {}))
        original_data = struct_to_bytes(struct_instance)

        # Apply mutation
        mutated_data, mutation_name = self._mutator.mutate_with_name(original_data, rng)

        return FuzzCase(
            target=self.name,
            operation=operation,
            input_data=mutated_data,
            seed=seed,
            mutation=mutation_name,
        )

    def execute(self, case: FuzzCase) -> FuzzResult:
        """Execute an ioctl fuzz case."""
        ioctl_def = self._ioctls.get_definition(case.operation)
        if ioctl_def is None:
            return FuzzResult(
                case=case,
                status=FuzzStatus.ERROR,
                error_message=f"Unknown operation: {case.operation}",
            )

        start_time = time.perf_counter()

        try:
            result_data = execute_ioctl_raw(
                self._device.kfd_fd,
                ioctl_def,
                case.input_data,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            return FuzzResult(
                case=case,
                status=FuzzStatus.OK,
                duration_ms=elapsed_ms,
                return_data=result_data,
            )

        except RuntimeError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            error_msg = str(e)

            # Check if this is an expected rejection vs unexpected error
            is_expected = any(exp in error_msg for exp in EXPECTED_ERRORS)
            status = FuzzStatus.OK if is_expected else FuzzStatus.ERROR

            return FuzzResult(
                case=case,
                status=status,
                duration_ms=elapsed_ms,
                error_message=error_msg,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return FuzzResult(
                case=case,
                status=FuzzStatus.ERROR,
                duration_ms=elapsed_ms,
                error_message=f"Unexpected: {type(e).__name__}: {e}",
            )
