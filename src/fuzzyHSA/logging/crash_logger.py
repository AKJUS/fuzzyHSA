# SPDX-License-Identifier: Apache-2.0
"""Crash logging to JSON files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..fuzz.types import FuzzResult


@dataclass
class CrashLogger:
    """
    Log crash results to JSON files.

    Creates files like: crashes/crash_20240321_143052_abc123.json
    """

    output_dir: Path

    def __post_init__(self):
        self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def log(self, result: FuzzResult) -> Path:
        """
        Log a fuzz result to a JSON file.

        Args:
            result: The FuzzResult to log

        Returns:
            Path to the created log file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        seed_hex = f"{result.case.seed:08x}"
        filename = f"crash_{timestamp}_{seed_hex}.json"
        path = self.output_dir / filename

        data = {
            "timestamp": datetime.now().isoformat(),
            "result": result.to_dict(),
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        return path

    def load(self, path: Path) -> FuzzResult:
        """
        Load a FuzzResult from a log file.

        Args:
            path: Path to the JSON file

        Returns:
            The reconstructed FuzzResult
        """
        from ..fuzz.types import FuzzResult

        with open(path) as f:
            data = json.load(f)

        return FuzzResult.from_dict(data["result"])

    def list_crashes(self) -> list[Path]:
        """List all crash log files."""
        return sorted(self.output_dir.glob("crash_*.json"))

    def get_latest(self) -> Path | None:
        """Get the most recent crash log."""
        crashes = self.list_crashes()
        return crashes[-1] if crashes else None
