# SPDX-License-Identifier: Apache-2.0
"""Unit tests for mutation strategies."""

import random
import pytest
from fuzzyHSA.fuzz.mutators import (
    BitflipMutator,
    ByteflipMutator,
    BoundaryMutator,
    ArithmeticMutator,
    ZeroMutator,
    CompositeMutator,
    create_default_mutator,
)


class TestBitflipMutator:
    def test_changes_data(self, zero_data):
        mutator = BitflipMutator()
        rng = random.Random(42)
        result = mutator.mutate(zero_data, rng)
        assert result != zero_data
        assert len(result) == len(zero_data)

    def test_preserves_length(self, sample_data):
        mutator = BitflipMutator()
        rng = random.Random(42)
        result = mutator.mutate(sample_data, rng)
        assert len(result) == len(sample_data)

    def test_empty_data(self):
        mutator = BitflipMutator()
        rng = random.Random(42)
        result = mutator.mutate(b"", rng)
        assert result == b""

    def test_reproducible_with_seed(self, sample_data):
        mutator = BitflipMutator()
        result1 = mutator.mutate(sample_data, random.Random(42))
        result2 = mutator.mutate(sample_data, random.Random(42))
        assert result1 == result2

    def test_different_seeds_different_results(self, sample_data):
        mutator = BitflipMutator()
        result1 = mutator.mutate(sample_data, random.Random(42))
        result2 = mutator.mutate(sample_data, random.Random(123))
        assert result1 != result2


class TestByteflipMutator:
    def test_changes_data(self, zero_data):
        mutator = ByteflipMutator()
        rng = random.Random(42)
        result = mutator.mutate(zero_data, rng)
        assert result != zero_data

    def test_preserves_length(self, sample_data):
        mutator = ByteflipMutator()
        rng = random.Random(42)
        result = mutator.mutate(sample_data, rng)
        assert len(result) == len(sample_data)

    def test_empty_data(self):
        mutator = ByteflipMutator()
        rng = random.Random(42)
        result = mutator.mutate(b"", rng)
        assert result == b""


class TestBoundaryMutator:
    def test_changes_data(self, sample_data):
        mutator = BoundaryMutator()
        rng = random.Random(42)
        result = mutator.mutate(sample_data, rng)
        assert result != sample_data

    def test_preserves_length(self, sample_data):
        mutator = BoundaryMutator()
        rng = random.Random(42)
        result = mutator.mutate(sample_data, rng)
        assert len(result) == len(sample_data)

    def test_uses_boundary_values(self, zero_data):
        mutator = BoundaryMutator()
        # Run many times and check we see boundary values
        seen_values = set()
        for seed in range(100):
            result = mutator.mutate(zero_data, random.Random(seed))
            seen_values.update(result)

        # Should see some boundary values like 0xFF, 0x7F, 0x80
        boundary_bytes = {0x00, 0x01, 0x7F, 0x80, 0xFF}
        assert len(seen_values & boundary_bytes) > 0


class TestArithmeticMutator:
    def test_changes_data(self, sample_data):
        mutator = ArithmeticMutator()
        rng = random.Random(42)
        result = mutator.mutate(sample_data, rng)
        assert result != sample_data

    def test_preserves_length(self, sample_data):
        mutator = ArithmeticMutator()
        rng = random.Random(42)
        result = mutator.mutate(sample_data, rng)
        assert len(result) == len(sample_data)


class TestZeroMutator:
    def test_creates_zeros(self, sample_data):
        mutator = ZeroMutator()
        rng = random.Random(42)
        result = mutator.mutate(sample_data, rng)
        assert result != sample_data
        # Should have at least some zeros
        assert b"\x00" in result

    def test_preserves_length(self, sample_data):
        mutator = ZeroMutator()
        rng = random.Random(42)
        result = mutator.mutate(sample_data, rng)
        assert len(result) == len(sample_data)


class TestCompositeMutator:
    def test_uses_different_strategies(self, sample_data):
        mutator = CompositeMutator()
        results = set()
        for seed in range(50):
            result = mutator.mutate(sample_data, random.Random(seed))
            results.add(result)
        # Should produce variety
        assert len(results) > 10

    def test_mutate_with_name(self, sample_data):
        mutator = CompositeMutator()
        rng = random.Random(42)
        result, name = mutator.mutate_with_name(sample_data, rng)
        assert isinstance(result, bytes)
        assert isinstance(name, str)
        assert name in ["bitflip", "byteflip", "boundary", "arithmetic", "zero"]

    def test_create_default_mutator(self):
        mutator = create_default_mutator()
        assert isinstance(mutator, CompositeMutator)
        assert len(mutator.mutators) == 5
