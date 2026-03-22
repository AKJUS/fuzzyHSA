# SPDX-License-Identifier: Apache-2.0
"""Unit tests for crash logging."""

import json

from fuzzyHSA.fuzz.types import FuzzCase, FuzzResult, FuzzStatus
from fuzzyHSA.logging import CrashLogger


class TestCrashLogger:
    def test_creates_output_dir(self, temp_dir):
        output = temp_dir / "crashes"
        CrashLogger(output)
        assert output.exists()

    def test_log_creates_file(self, temp_dir):
        logger = CrashLogger(temp_dir)
        case = FuzzCase("ioctl", "test_op", b"\xde\xad\xbe\xef", 42, "bitflip")
        result = FuzzResult(case, FuzzStatus.CRASH, 10.5, "GPU error")

        path = logger.log(result)

        assert path.exists()
        assert path.suffix == ".json"
        assert "crash_" in path.name

    def test_log_content(self, temp_dir):
        logger = CrashLogger(temp_dir)
        case = FuzzCase("ioctl", "test_op", b"\x00\x01", 123, "boundary")
        result = FuzzResult(case, FuzzStatus.HANG, 5000.0)

        path = logger.log(result)

        with open(path) as f:
            data = json.load(f)

        assert "timestamp" in data
        assert data["result"]["case"]["operation"] == "test_op"
        assert data["result"]["case"]["seed"] == 123
        assert data["result"]["status"] == "hang"

    def test_load(self, temp_dir):
        logger = CrashLogger(temp_dir)
        case = FuzzCase("ioctl", "alloc", b"\xff\xfe\xfd", 999, "zero")
        original = FuzzResult(
            case, FuzzStatus.CRASH, 100.0, "test error", ["dmesg line"]
        )

        path = logger.log(original)
        loaded = logger.load(path)

        assert loaded.case.target == original.case.target
        assert loaded.case.operation == original.case.operation
        assert loaded.case.input_data == original.case.input_data
        assert loaded.case.seed == original.case.seed
        assert loaded.status == original.status
        assert loaded.error_message == original.error_message

    def test_list_crashes(self, temp_dir):
        logger = CrashLogger(temp_dir)
        FuzzCase("ioctl", "test", b"", 0, "none")

        # Log several crashes
        for i in range(3):
            result = FuzzResult(
                FuzzCase("ioctl", "test", b"", i, "none"),
                FuzzStatus.CRASH
            )
            logger.log(result)

        crashes = logger.list_crashes()
        assert len(crashes) == 3

    def test_get_latest(self, temp_dir):
        logger = CrashLogger(temp_dir)

        # Initially no crashes
        assert logger.get_latest() is None

        # Add a crash
        result = FuzzResult(
            FuzzCase("ioctl", "test", b"", 42, "none"),
            FuzzStatus.CRASH
        )
        path = logger.log(result)

        assert logger.get_latest() == path
