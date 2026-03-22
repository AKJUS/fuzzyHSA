# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the fuzz harness (with mocked target)."""

import pytest
from unittest.mock import Mock, MagicMock
from fuzzyHSA.fuzz.types import FuzzCase, FuzzResult, FuzzStatus
from fuzzyHSA.fuzz.harness import FuzzHarness, HarnessConfig


class MockTarget:
    """Mock fuzz target for testing harness logic."""

    def __init__(self, results=None):
        self.name = "mock"
        self.operations = ["op1", "op2", "op3"]
        self._results = results or []
        self._call_count = 0

    def generate_case(self, seed, operation=None):
        return FuzzCase(
            target=self.name,
            operation=operation or "op1",
            input_data=b"\x00" * 16,
            seed=seed,
            mutation="mock",
        )

    def execute(self, case):
        if self._call_count < len(self._results):
            result = self._results[self._call_count]
        else:
            result = FuzzResult(case, FuzzStatus.OK, 1.0)
        self._call_count += 1
        return result


class TestHarnessConfig:
    def test_defaults(self):
        config = HarnessConfig()
        assert config.iterations == 1000
        assert config.seed is None
        assert config.stop_on_crash is True
        assert config.verbose is False

    def test_custom_values(self):
        config = HarnessConfig(
            iterations=100,
            seed=42,
            stop_on_crash=False,
            verbose=True,
        )
        assert config.iterations == 100
        assert config.seed == 42


class TestFuzzHarness:
    def test_runs_iterations(self):
        target = MockTarget()
        config = HarnessConfig(iterations=10, verbose=False)
        harness = FuzzHarness(target, config)

        results = harness.run()

        assert harness.stats.total_cases == 10
        assert harness.stats.ok_count == 10
        assert len(results) == 0  # No interesting results

    def test_stops_on_crash(self):
        case = FuzzCase("mock", "op1", b"", 0, "mock")
        crash_results = [
            FuzzResult(case, FuzzStatus.OK, 1.0),
            FuzzResult(case, FuzzStatus.OK, 1.0),
            FuzzResult(case, FuzzStatus.CRASH, 1.0, "GPU crashed"),
            FuzzResult(case, FuzzStatus.OK, 1.0),  # Should not reach
        ]
        target = MockTarget(crash_results)
        config = HarnessConfig(iterations=100, stop_on_crash=True, verbose=False)
        harness = FuzzHarness(target, config)

        results = harness.run()

        assert harness.stats.total_cases == 3
        assert harness.stats.crash_count == 1
        assert len(results) == 1
        assert results[0].status == FuzzStatus.CRASH

    def test_continues_on_crash_if_configured(self):
        case = FuzzCase("mock", "op1", b"", 0, "mock")
        crash_results = [
            FuzzResult(case, FuzzStatus.OK, 1.0),
            FuzzResult(case, FuzzStatus.CRASH, 1.0),
            FuzzResult(case, FuzzStatus.OK, 1.0),
            FuzzResult(case, FuzzStatus.CRASH, 1.0),
            FuzzResult(case, FuzzStatus.OK, 1.0),
        ]
        target = MockTarget(crash_results)
        config = HarnessConfig(iterations=5, stop_on_crash=False, verbose=False)
        harness = FuzzHarness(target, config)

        results = harness.run()

        assert harness.stats.total_cases == 5
        assert harness.stats.crash_count == 2
        assert len(results) == 2

    def test_detects_hang_by_duration(self):
        case = FuzzCase("mock", "op1", b"", 0, "mock")
        target = MockTarget([
            FuzzResult(case, FuzzStatus.OK, 1.0),
            FuzzResult(case, FuzzStatus.OK, 10000.0),  # Long duration
        ])
        config = HarnessConfig(
            iterations=10,
            stop_on_hang=True,
            hang_timeout_ms=5000.0,
            verbose=False,
        )
        harness = FuzzHarness(target, config)

        results = harness.run()

        assert harness.stats.total_cases == 2
        assert harness.stats.hang_count == 1

    def test_uses_seed_for_reproducibility(self):
        target = MockTarget()
        config = HarnessConfig(iterations=5, seed=12345, verbose=False)
        harness = FuzzHarness(target, config)

        harness.run()
        stats1 = harness.stats

        # Reset and run again with same seed
        target._call_count = 0
        harness = FuzzHarness(target, HarnessConfig(iterations=5, seed=12345, verbose=False))
        harness.run()
        stats2 = harness.stats

        assert stats1.total_cases == stats2.total_cases

    def test_run_single(self):
        target = MockTarget()
        harness = FuzzHarness(target, HarnessConfig())

        result = harness.run_single(seed=42, operation="op2")

        assert result.case.seed == 42
        assert result.case.operation == "op2"
        assert result.status == FuzzStatus.OK

    def test_stop(self):
        target = MockTarget()
        config = HarnessConfig(iterations=1000000, verbose=False)
        harness = FuzzHarness(target, config)

        # Stop immediately
        harness.stop()
        harness._running = False

        results = harness.run()
        # Should stop quickly (though may run a few iterations)
        assert harness.stats.total_cases < 1000

    def test_uses_crash_logger(self, temp_dir):
        from fuzzyHSA.logging import CrashLogger

        case = FuzzCase("mock", "op1", b"", 0, "mock")
        target = MockTarget([
            FuzzResult(case, FuzzStatus.CRASH, 1.0, "test crash"),
        ])
        logger = CrashLogger(temp_dir)
        config = HarnessConfig(iterations=1, verbose=False)
        harness = FuzzHarness(target, config, logger=logger)

        harness.run()

        # Should have logged the crash
        crashes = logger.list_crashes()
        assert len(crashes) == 1
