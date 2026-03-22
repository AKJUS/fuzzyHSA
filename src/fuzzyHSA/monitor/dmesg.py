# SPDX-License-Identifier: Apache-2.0
"""Kernel log (dmesg) monitoring for crash detection."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from re import Pattern

# Patterns that indicate GPU-related errors
GPU_ERROR_PATTERNS = (
    "amdgpu:",
    "kfd:",
    "drm:",
    "GPU fault",
    "gpu hang",
    "ring buffer",
    "VMFAULT",
    "INTERRUPT",
    "ECC error",
    "page fault",
)


@dataclass
class DmesgMonitor:
    """
    Monitor dmesg for GPU-related errors.

    Uses compiled regex for efficient pattern matching.

    Usage:
        monitor = DmesgMonitor()
        monitor.clear()  # Set baseline
        # ... do fuzzing ...
        _, errors = monitor.check()  # Single dmesg read
        if errors:
            print(errors)
    """

    patterns: tuple[str, ...] = GPU_ERROR_PATTERNS
    _baseline_lines: int = field(default=0, repr=False)
    _pattern_regex: Pattern[str] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Compile patterns into single regex for efficient matching."""
        escaped = [re.escape(p) for p in self.patterns]
        self._pattern_regex = re.compile("|".join(escaped), re.IGNORECASE)

    def clear(self) -> None:
        """Set baseline - future checks will only see new messages."""
        self._baseline_lines = len(self._read_dmesg().splitlines())

    def check(self) -> tuple[list[str], list[str]]:
        """
        Check for new messages (single dmesg read).

        Returns:
            Tuple of (new_messages, gpu_errors)
        """
        lines = self._read_dmesg().splitlines()
        messages = lines if self._baseline_lines > len(lines) else lines[self._baseline_lines:]
        errors = [m for m in messages if self._pattern_regex and self._pattern_regex.search(m)]
        return messages, errors

    def get_new_messages(self) -> list[str]:
        """Get dmesg messages since last clear."""
        messages, _ = self.check()
        return messages

    def has_gpu_error(self) -> bool:
        """Check if any new messages match GPU error patterns."""
        _, errors = self.check()
        return bool(errors)

    def get_gpu_errors(self) -> list[str]:
        """Get only messages that match GPU error patterns."""
        _, errors = self.check()
        return errors

    def _read_dmesg(self) -> str:
        """Read current dmesg output."""
        try:
            result = subprocess.run(
                ["dmesg"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            return ""
