"""Secwave command codes (Spec Table 7)."""

from __future__ import annotations

from enum import IntEnum


class SecwaveCommand(IntEnum):
    """Fixed Secwave command codes; 0 means flexible function."""

    FLEXIBLE = 0x0000
    CLOSE = 0x0008
    OPEN = 0x0010
    HALT = 0x0018
    PULSE_INTERMEDIATE_CLOSED = 0x0020
    PULSE_INTERMEDIATE_OPENED = 0x0021
    PULSE = 0x0038
    LIGHT = 0x0042
    LIGHT_TIMER = 0x0043
    VACATION_MODE = 0x004A
