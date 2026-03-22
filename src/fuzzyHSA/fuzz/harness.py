# SPDX-License-Identifier: Apache-2.0
"""Fuzzing harness - orchestrates fuzz test execution."""

from __future__ import annotations

import random
import signal
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .types import FuzzResult, FuzzStats, FuzzStatus

if TYPE_CHECKING:
    from ..logging.crash_logger import CrashLogger
    from ..monitor.dmesg import DmesgMonitor
    from .targets.base import FuzzTarget


@dataclass
class HarnessConfig:
    """Configuration for the fuzz harness."""

    iterations: int = 1000
    seed: int | None = None
    stop_on_crash: bool = True
    stop_on_hang: bool = True
    hang_timeout_ms: float = 5000.0
    verbose: bool = False
    operations: list[str] | None = None  # None = all operations


class FuzzHarness:
    """
    Main fuzzing harness.

    Orchestrates:
    - Test case generation
    - Execution against target
    - Crash detection via monitor
    - Result logging

    Supports graceful shutdown via SIGINT/SIGTERM.
    """

    def __init__(
        self,
        target: FuzzTarget,
        config: HarnessConfig | None = None,
        monitor: DmesgMonitor | None = None,
        logger: CrashLogger | None = None,
    ):
        self._target = target
        self._config = config or HarnessConfig()
        self._monitor = monitor
        self._logger = logger
        self._stats = FuzzStats()
        self._running = False
        self._original_sigint = None
        self._original_sigterm = None

    @property
    def stats(self) -> FuzzStats:
        """Get current fuzzing statistics."""
        return self._stats

    @property
    def is_running(self) -> bool:
        """Check if fuzzing loop is active."""
        return self._running

    def _setup_signal_handlers(self) -> None:
        """Install signal handlers for graceful shutdown."""
        def handler(signum: int, frame) -> None:
            if self._config.verbose:
                sig_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
                print(f"\n[*] Received {sig_name}, stopping gracefully...")
            self._running = False

        self._original_sigint = signal.signal(signal.SIGINT, handler)
        self._original_sigterm = signal.signal(signal.SIGTERM, handler)

    def _restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        if self._original_sigint is not None:
            signal.signal(signal.SIGINT, self._original_sigint)
        if self._original_sigterm is not None:
            signal.signal(signal.SIGTERM, self._original_sigterm)

    def run(self) -> list[FuzzResult]:
        """
        Run the fuzzing loop.

        Returns:
            List of interesting results (crashes, hangs)
        """
        self._running = True
        self._setup_signal_handlers()
        interesting_results: list[FuzzResult] = []

        try:
            interesting_results = self._run_loop()
        finally:
            self._running = False
            self._restore_signal_handlers()

        return interesting_results

    def _run_loop(self) -> list[FuzzResult]:
        """Internal fuzzing loop."""
        interesting_results: list[FuzzResult] = []

        # Initialize RNG
        seed = self._config.seed if self._config.seed is not None else int(time.time())
        rng = random.Random(seed)

        # Get operations to fuzz
        operations = self._config.operations or self._target.operations
        if not operations:
            if self._config.verbose:
                print("Error: No operations available to fuzz")
            return []

        if self._config.verbose:
            print(f"Fuzzing: target={self._target.name}, ops={len(operations)}, seed={seed}")

        # Clear monitor baseline if present
        if self._monitor:
            self._monitor.clear()

        for i in range(self._config.iterations):
            if not self._running:
                if self._config.verbose:
                    print(f"Stopped at iteration {i}")
                break

            # Generate case
            case_seed = rng.randint(0, 2**32 - 1)
            operation = rng.choice(operations)
            case = self._target.generate_case(case_seed, operation)

            # Execute
            result = self._target.execute(case)

            # Check for GPU errors in dmesg (single read via check())
            if self._monitor:
                _, errors = self._monitor.check()
                if errors:
                    result.status = FuzzStatus.CRASH
                    result.dmesg_output = errors
                    self._monitor.clear()

            # Check for hang (duration exceeds threshold)
            if result.duration_ms > self._config.hang_timeout_ms:
                result.status = FuzzStatus.HANG

            # Record stats
            self._stats.record(result)

            # Handle interesting results
            if result.is_interesting:
                interesting_results.append(result)

                if self._logger:
                    path = self._logger.log(result)
                    if self._config.verbose:
                        print(f"[!] {result.status.value}: {result.case.operation} -> {path.name}")

                if result.status == FuzzStatus.CRASH and self._config.stop_on_crash:
                    if self._config.verbose:
                        print("Stopping: crash detected")
                    break

                if result.status == FuzzStatus.HANG and self._config.stop_on_hang:
                    if self._config.verbose:
                        print("Stopping: hang detected")
                    break

            # Progress output
            if self._config.verbose and (i + 1) % 100 == 0:
                rate = self._stats.cases_per_second
                print(f"[{i + 1}/{self._config.iterations}] {rate:.1f}/s, crashes={self._stats.crash_count}")

        if self._config.verbose:
            print(f"Done: {self._stats}")

        return interesting_results

    def stop(self) -> None:
        """Stop the fuzzing loop gracefully."""
        self._running = False

    def run_single(self, seed: int, operation: str | None = None) -> FuzzResult:
        """
        Run a single fuzz case (useful for reproduction).

        Args:
            seed: Seed for the case
            operation: Specific operation, or None for random (based on seed)
        """
        case = self._target.generate_case(seed, operation)
        return self._target.execute(case)

    def __enter__(self) -> FuzzHarness:
        """Support context manager usage."""
        return self

    def __exit__(self, *_) -> None:
        """Ensure fuzzing stops on context exit."""
        self.stop()
