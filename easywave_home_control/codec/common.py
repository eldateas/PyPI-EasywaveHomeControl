"""Shared helpers for EWB state word parsing and encoding."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum


class StateDirection(IntEnum):
    """Whether a state word is read from the device or written to it."""

    FROM_DEVICE = 0
    TO_DEVICE = 1


@dataclass(frozen=True)
class TimerDuration:
    """Duration encoded as mantissa and exponent (Spec: t = factor * m * 2^x)."""

    mantissa: int
    exponent: int
    factor_minutes: float = 0.125

    @property
    def total_minutes(self) -> float:
        if self.exponent == 0:
            return self.factor_minutes * self.mantissa
        return self.factor_minutes * self.mantissa * (2**self.exponent)

    @property
    def total_seconds(self) -> float:
        return self.total_minutes * 60.0

    @classmethod
    def from_duration_minutes(
        cls, minutes: float, *, factor_minutes: float = 0.125
    ) -> TimerDuration:
        if minutes <= 0:
            return cls(mantissa=0, exponent=0, factor_minutes=factor_minutes)
        ratio = minutes / factor_minutes
        exponent = 0
        while ratio >= 256 and exponent < 15:
            ratio /= 2
            exponent += 1
        mantissa = int(round(ratio))
        if mantissa >= 256:
            mantissa = 255
            exponent = min(exponent + 1, 15)
        return cls(mantissa=mantissa, exponent=exponent, factor_minutes=factor_minutes)


def state_word(state_bytes: bytes) -> int:
    if len(state_bytes) != 4:
        raise ValueError(f"State must be 4 bytes, got {len(state_bytes)}")
    return struct.unpack(">I", state_bytes)[0]


def encode_state_word(word: int) -> bytes:
    return struct.pack(">I", word & 0xFFFFFFFF)


def get_bits(word: int, high: int, low: int) -> int:
    width = high - low + 1
    return (word >> low) & ((1 << width) - 1)


def set_bits(word: int, high: int, low: int, value: int) -> int:
    width = high - low + 1
    mask = ((1 << width) - 1) << low
    return (word & ~mask) | ((value & ((1 << width) - 1)) << low)


def parse_timer_high_low(
    word: int, exp_high: int, exp_low: int, man_high: int, man_low: int
) -> TimerDuration:
    return TimerDuration(
        mantissa=get_bits(word, man_high, man_low),
        exponent=get_bits(word, exp_high, exp_low),
    )


def encode_timer_high_low(
    word: int,
    duration: TimerDuration,
    exp_high: int,
    exp_low: int,
    man_high: int,
    man_low: int,
) -> int:
    word = set_bits(word, exp_high, exp_low, duration.exponent)
    return set_bits(word, man_high, man_low, duration.mantissa)
