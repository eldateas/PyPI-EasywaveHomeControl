"""Secwave primary state word (Spec Table 8)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from ..common import get_bits, set_bits


class SecwavePosition(IntEnum):
    OTHER = 0
    BELOW_LOWER_INTERMEDIATE = 1
    ABOVE_UPPER_INTERMEDIATE = 2
    BETWEEN_INTERMEDIATES = 3
    END_CLOSED = 4
    LOWER_INTERMEDIATE = 5
    UPPER_INTERMEDIATE = 6
    END_OPENED = 7


class SecwaveMovement(IntEnum):
    STOPPED = 0
    MOVING = 1
    STARTING = 2
    STOPPING = 3


def _parse_position(value: int) -> SecwavePosition | int:
    try:
        return SecwavePosition(value)
    except ValueError:
        return value


def _parse_movement(value: int) -> SecwaveMovement | int:
    try:
        return SecwaveMovement(value)
    except ValueError:
        return value


@dataclass(frozen=True)
class SecwavePrimaryState:
    position: SecwavePosition | int
    opening: bool
    movement: SecwaveMovement | int
    vacation_mode_off: bool

    @property
    def vacation_mode_on(self) -> bool:
        return not self.vacation_mode_off


def parse_primary_state(word: int) -> SecwavePrimaryState:
    return SecwavePrimaryState(
        position=_parse_position(get_bits(word, 2, 0)),
        opening=bool((word >> 6) & 1),
        movement=_parse_movement(get_bits(word, 8, 7)),
        vacation_mode_off=bool((word >> 11) & 1),
    )


def encode_primary_state(state: SecwavePrimaryState) -> int:
    """Encode primary state word; reserved bits cleared per Spec."""
    word = 0
    position = int(state.position) if isinstance(state.position, SecwavePosition) else state.position
    movement = int(state.movement) if isinstance(state.movement, SecwaveMovement) else state.movement
    word = set_bits(word, 2, 0, position)
    if state.opening:
        word = set_bits(word, 6, 6, 1)
    word = set_bits(word, 8, 7, movement)
    if state.vacation_mode_off:
        word = set_bits(word, 11, 11, 1)
    return word & 0xFFFF


@dataclass(frozen=True)
class SecwaveReplyState:
    primary: SecwavePrimaryState
    secondary: int = 0


def parse_reply_state(primary_word: int, secondary_word: int = 0) -> SecwaveReplyState:
    return SecwaveReplyState(
        primary=parse_primary_state(primary_word),
        secondary=secondary_word & 0xFFFF,
    )


def encode_reply_state(state: SecwaveReplyState) -> tuple[int, int]:
    return encode_primary_state(state.primary), state.secondary & 0xFFFF
