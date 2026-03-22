# SPDX-License-Identifier: Apache-2.0
"""Core data types for fuzzing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FuzzStatus(str, Enum):
    """Result status of a fuzz case execution."""

    OK = "ok"
    CRASH = "crash"
    HANG = "hang"
    ERROR = "error"


@dataclass(frozen=True)
class FuzzCase:
    """
    A single fuzz test case.

    Immutable so it can be logged/reproduced exactly.
    """

    target: str  # e.g., "ioctl"
    operation: str  # e.g., "alloc_memory_of_gpu"
    input_data: bytes  # The (possibly mutated) input
    seed: int  # Random seed for reproduction
    mutation: str  # Description of mutation applied

    def __repr__(self) -> str:
        return (
            f"FuzzCase(target={self.target!r}, op={self.operation!r}, "
            f"seed={self.seed}, mutation={self.mutation!r}, "
            f"data={len(self.input_data)}B)"
        )


@dataclass
class FuzzResult:
    """
    Result of executing a fuzz case.

    Mutable to allow adding details during execution.
    """

    case: FuzzCase
    status: FuzzStatus
    duration_ms: float = 0.0
    error_message: str | None = None
    dmesg_output: list[str] = field(default_factory=list)
    return_data: bytes | None = None

    @property
    def is_interesting(self) -> bool:
        """Returns True if this result indicates a potential bug."""
        return self.status in (FuzzStatus.CRASH, FuzzStatus.HANG)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "case": {
                "target": self.case.target,
                "operation": self.case.operation,
                "input_data": self.case.input_data.hex(),
                "seed": self.case.seed,
                "mutation": self.case.mutation,
            },
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "dmesg_output": self.dmesg_output,
            "return_data": self.return_data.hex() if self.return_data else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FuzzResult:
        """Create from JSON dict."""
        case = FuzzCase(
            target=data["case"]["target"],
            operation=data["case"]["operation"],
            input_data=bytes.fromhex(data["case"]["input_data"]),
            seed=data["case"]["seed"],
            mutation=data["case"]["mutation"],
        )
        return cls(
            case=case,
            status=FuzzStatus(data["status"]),
            duration_ms=data.get("duration_ms", 0.0),
            error_message=data.get("error_message"),
            dmesg_output=data.get("dmesg_output", []),
            return_data=bytes.fromhex(data["return_data"]) if data.get("return_data") else None,
        )


@dataclass
class FuzzStats:
    """Statistics for a fuzzing session."""

    total_cases: int = 0
    total_duration_ms: float = 0.0
    _counts: dict[FuzzStatus, int] = field(default_factory=lambda: {s: 0 for s in FuzzStatus})

    @property
    def ok_count(self) -> int: return self._counts[FuzzStatus.OK]
    @property
    def crash_count(self) -> int: return self._counts[FuzzStatus.CRASH]
    @property
    def hang_count(self) -> int: return self._counts[FuzzStatus.HANG]
    @property
    def error_count(self) -> int: return self._counts[FuzzStatus.ERROR]

    def record(self, result: FuzzResult) -> None:
        """Record a result into stats."""
        self.total_cases += 1
        self.total_duration_ms += result.duration_ms
        self._counts[result.status] += 1

    @property
    def cases_per_second(self) -> float:
        """Average execution rate."""
        if self.total_duration_ms == 0:
            return 0.0
        return self.total_cases / (self.total_duration_ms / 1000)

    def __repr__(self) -> str:
        return (
            f"FuzzStats(total={self.total_cases}, ok={self.ok_count}, "
            f"crash={self.crash_count}, hang={self.hang_count}, "
            f"error={self.error_count}, rate={self.cases_per_second:.1f}/s)"
        )
