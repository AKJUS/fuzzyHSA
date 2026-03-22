# SPDX-License-Identifier: Apache-2.0
"""Mutation strategies for fuzzing."""

from __future__ import annotations

import random
import struct
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@runtime_checkable
class Mutator(Protocol):
    """Protocol for mutation strategies."""

    name: str

    def mutate(self, data: bytes, rng: random.Random) -> bytes:
        """Mutate data using the given RNG."""
        ...


def _mutate(data: bytes, fn) -> bytes:
    """Common mutator wrapper: handle empty data and convert to/from bytearray."""
    if not data:
        return data
    buf = bytearray(data)
    fn(buf)
    return bytes(buf)


@dataclass
class BitflipMutator:
    """Flip random bits in the data."""

    name: str = "bitflip"
    max_flips: int = 8

    def mutate(self, data: bytes, rng: random.Random) -> bytes:
        def flip(buf: bytearray) -> None:
            for _ in range(rng.randint(1, min(self.max_flips, len(buf) * 8))):
                buf[rng.randrange(len(buf))] ^= 1 << rng.randrange(8)
        return _mutate(data, flip)


@dataclass
class ByteflipMutator:
    """Replace random bytes with random values."""

    name: str = "byteflip"
    max_bytes: int = 4

    def mutate(self, data: bytes, rng: random.Random) -> bytes:
        def flip(buf: bytearray) -> None:
            for _ in range(rng.randint(1, min(self.max_bytes, len(buf)))):
                buf[rng.randrange(len(buf))] = rng.randint(0, 255)
        return _mutate(data, flip)


# Boundary values lookup: size -> (format, values)
_BOUNDARY_TABLE = {
    1: (None, (0x00, 0x01, 0x7F, 0x80, 0xFF)),
    2: ("<H", (0x0000, 0x0001, 0x7FFF, 0x8000, 0xFFFF)),
    4: ("<I", (0x00000000, 0x00000001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)),
    8: ("<Q", (0x0000000000000000, 0x0000000000000001, 0x7FFFFFFFFFFFFFFF,
              0x8000000000000000, 0xFFFFFFFFFFFFFFFF)),
}

# Arithmetic formats lookup: size -> (format, mask)
_ARITH_TABLE = {
    1: (None, 0xFF),
    2: ("<H", 0xFFFF),
    4: ("<I", 0xFFFFFFFF),
}


@dataclass
class BoundaryMutator:
    """Replace fields with boundary values."""

    name: str = "boundary"

    def mutate(self, data: bytes, rng: random.Random) -> bytes:
        def apply(buf: bytearray) -> None:
            valid_sizes = [s for s in (1, 2, 4, 8) if s <= len(buf)]
            if not valid_sizes:
                return
            size = rng.choice(valid_sizes)
            max_offset = len(buf) - size
            if max_offset < 0:
                return
            offset = rng.randrange((max_offset // size) + 1) * size
            if offset + size > len(buf):
                return
            fmt, values = _BOUNDARY_TABLE[size]
            value = rng.choice(values)
            if fmt is None:
                buf[offset] = value
            else:
                struct.pack_into(fmt, buf, offset, value)
        return _mutate(data, apply)


@dataclass
class ArithmeticMutator:
    """Add/subtract small values from fields."""

    name: str = "arithmetic"
    max_delta: int = 35

    def mutate(self, data: bytes, rng: random.Random) -> bytes:
        def apply(buf: bytearray) -> None:
            valid_sizes = [s for s in (1, 2, 4) if s <= len(buf)]
            if not valid_sizes:
                return
            size = rng.choice(valid_sizes)
            max_offset = len(buf) - size
            if max_offset < 0:
                return
            offset = rng.randrange(max_offset + 1)
            delta = rng.randint(-self.max_delta, self.max_delta) or 1
            fmt, mask = _ARITH_TABLE[size]
            if fmt is None:
                buf[offset] = (buf[offset] + delta) & mask
            else:
                value = struct.unpack_from(fmt, buf, offset)[0]
                struct.pack_into(fmt, buf, offset, (value + delta) & mask)
        return _mutate(data, apply)


@dataclass
class ZeroMutator:
    """Zero out chunks of data."""

    name: str = "zero"
    max_size: int = 16

    def mutate(self, data: bytes, rng: random.Random) -> bytes:
        def apply(buf: bytearray) -> None:
            size = rng.randint(1, min(self.max_size, len(buf)))
            max_offset = len(buf) - size
            offset = rng.randrange(max_offset + 1) if max_offset >= 0 else 0
            buf[offset:offset + size] = b"\x00" * size
        return _mutate(data, apply)


@dataclass
class CompositeMutator:
    """Combines multiple mutation strategies."""

    name: str = "composite"
    mutators: list[Mutator] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.mutators:
            self.mutators = [
                BitflipMutator(),
                ByteflipMutator(),
                BoundaryMutator(),
                ArithmeticMutator(),
                ZeroMutator(),
            ]

    def mutate(self, data: bytes, rng: random.Random) -> bytes:
        mutator = rng.choice(self.mutators)
        return mutator.mutate(data, rng)

    def mutate_with_name(self, data: bytes, rng: random.Random) -> tuple[bytes, str]:
        """Mutate and return both result and mutator name."""
        mutator = rng.choice(self.mutators)
        return mutator.mutate(data, rng), mutator.name
