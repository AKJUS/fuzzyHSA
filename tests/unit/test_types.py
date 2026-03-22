# SPDX-License-Identifier: Apache-2.0
"""Unit tests for fuzz types."""

import pytest
from fuzzyHSA.fuzz.types import FuzzCase, FuzzResult, FuzzStatus, FuzzStats


class TestFuzzCase:
    def test_creation(self):
        case = FuzzCase(
            target="ioctl",
            operation="alloc_memory_of_gpu",
            input_data=b"\x00\x01\x02",
            seed=42,
            mutation="bitflip",
        )
        assert case.target == "ioctl"
        assert case.operation == "alloc_memory_of_gpu"
        assert case.input_data == b"\x00\x01\x02"
        assert case.seed == 42
        assert case.mutation == "bitflip"

    def test_immutable(self):
        case = FuzzCase(
            target="ioctl",
            operation="test",
            input_data=b"",
            seed=0,
            mutation="none",
        )
        with pytest.raises(AttributeError):
            case.target = "other"

    def test_repr(self):
        case = FuzzCase(
            target="ioctl",
            operation="test_op",
            input_data=b"\x00" * 100,
            seed=12345,
            mutation="bitflip",
        )
        repr_str = repr(case)
        assert "ioctl" in repr_str
        assert "test_op" in repr_str
        assert "12345" in repr_str
        assert "100B" in repr_str


class TestFuzzResult:
    def test_creation(self):
        case = FuzzCase("ioctl", "test", b"", 0, "none")
        result = FuzzResult(case=case, status=FuzzStatus.OK, duration_ms=1.5)
        assert result.case == case
        assert result.status == FuzzStatus.OK
        assert result.duration_ms == 1.5

    def test_is_interesting(self):
        case = FuzzCase("ioctl", "test", b"", 0, "none")

        ok_result = FuzzResult(case=case, status=FuzzStatus.OK)
        assert not ok_result.is_interesting

        crash_result = FuzzResult(case=case, status=FuzzStatus.CRASH)
        assert crash_result.is_interesting

        hang_result = FuzzResult(case=case, status=FuzzStatus.HANG)
        assert hang_result.is_interesting

        error_result = FuzzResult(case=case, status=FuzzStatus.ERROR)
        assert not error_result.is_interesting

    def test_to_dict(self):
        case = FuzzCase("ioctl", "test_op", b"\x00\x01\x02", 42, "bitflip")
        result = FuzzResult(
            case=case,
            status=FuzzStatus.CRASH,
            duration_ms=10.5,
            error_message="GPU hung",
            dmesg_output=["amdgpu: error"],
        )
        d = result.to_dict()

        assert d["case"]["target"] == "ioctl"
        assert d["case"]["operation"] == "test_op"
        assert d["case"]["input_data"] == "000102"
        assert d["case"]["seed"] == 42
        assert d["status"] == "crash"
        assert d["duration_ms"] == 10.5
        assert d["error_message"] == "GPU hung"
        assert d["dmesg_output"] == ["amdgpu: error"]

    def test_from_dict(self):
        d = {
            "case": {
                "target": "ioctl",
                "operation": "test_op",
                "input_data": "deadbeef",
                "seed": 123,
                "mutation": "boundary",
            },
            "status": "crash",
            "duration_ms": 5.0,
            "error_message": "test error",
            "dmesg_output": ["line1", "line2"],
            "return_data": "cafebabe",
        }
        result = FuzzResult.from_dict(d)

        assert result.case.target == "ioctl"
        assert result.case.input_data == b"\xde\xad\xbe\xef"
        assert result.status == FuzzStatus.CRASH
        assert result.return_data == b"\xca\xfe\xba\xbe"


class TestFuzzStats:
    def test_initial_state(self):
        stats = FuzzStats()
        assert stats.total_cases == 0
        assert stats.ok_count == 0
        assert stats.crash_count == 0

    def test_record(self):
        stats = FuzzStats()
        case = FuzzCase("ioctl", "test", b"", 0, "none")

        stats.record(FuzzResult(case, FuzzStatus.OK, 10.0))
        stats.record(FuzzResult(case, FuzzStatus.OK, 10.0))
        stats.record(FuzzResult(case, FuzzStatus.CRASH, 5.0))
        stats.record(FuzzResult(case, FuzzStatus.HANG, 5000.0))
        stats.record(FuzzResult(case, FuzzStatus.ERROR, 1.0))

        assert stats.total_cases == 5
        assert stats.ok_count == 2
        assert stats.crash_count == 1
        assert stats.hang_count == 1
        assert stats.error_count == 1
        assert stats.total_duration_ms == 5026.0

    def test_cases_per_second(self):
        stats = FuzzStats()
        case = FuzzCase("ioctl", "test", b"", 0, "none")

        # 100 cases in 1000ms = 100/s
        for _ in range(100):
            stats.record(FuzzResult(case, FuzzStatus.OK, 10.0))

        assert stats.cases_per_second == 100.0

    def test_cases_per_second_zero_duration(self):
        stats = FuzzStats()
        assert stats.cases_per_second == 0.0
