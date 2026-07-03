"""Secwave flag and query field parsing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class SecLearnTelegramKind(IntEnum):
    NORMAL = 0
    LEARN_FROM_LEARNED = 1
    NEW_LEARN_IN_PROGRESS = 2
    NEW_LEARN_STORAGE_FULL = 3


@dataclass(frozen=True)
class SecQuery:
    wants_reply: bool
    reply_only: bool

    @classmethod
    def from_byte(cls, value: int) -> SecQuery:
        return cls(
            wants_reply=bool(value & 0x01),
            reply_only=bool(value & 0x80),
        )

    def to_byte(self) -> int:
        value = 0
        if self.wants_reply:
            value |= 0x01
        if self.reply_only:
            value |= 0x80
        return value


@dataclass(frozen=True)
class SecTransmitterFlags:
    low_battery: bool
    mobile: bool

    @classmethod
    def from_byte(cls, value: int) -> SecTransmitterFlags:
        return cls(
            low_battery=bool(value & 0x40),
            mobile=bool(value & 0x80),
        )

    def to_byte(self) -> int:
        value = 0
        if self.low_battery:
            value |= 0x40
        if self.mobile:
            value |= 0x80
        return value
