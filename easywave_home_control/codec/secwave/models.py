"""Secwave telegram and storage entry dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from .commands import SecwaveCommand
from .fields import SecLearnTelegramKind, SecQuery, SecTransmitterFlags
from .states import SecwaveReplyState


@dataclass(frozen=True)
class SecStorageEntry:
    storage_index: int
    is_used: bool
    user_data: int


@dataclass(frozen=True)
class SecCommandTelegram:
    storage_index: int
    query: SecQuery
    command: int
    user_data: int
    flags: SecTransmitterFlags
    learn_kind: SecLearnTelegramKind | int

    @property
    def is_flexible_command(self) -> bool:
        return self.command == 0

    @property
    def fixed_command(self) -> SecwaveCommand | None:
        if self.is_flexible_command:
            return None
        try:
            return SecwaveCommand(self.command)
        except ValueError:
            return None

    @property
    def is_learn_telegram(self) -> bool:
        return self.learn_kind != SecLearnTelegramKind.NORMAL

    @property
    def is_new_learn(self) -> bool:
        return self.learn_kind in (
            SecLearnTelegramKind.NEW_LEARN_IN_PROGRESS,
            SecLearnTelegramKind.NEW_LEARN_STORAGE_FULL,
        )


@dataclass(frozen=True)
class SecSendCmdTelRequest:
    button_number: int
    query: SecQuery
    command: int
    flags: SecTransmitterFlags


@dataclass(frozen=True)
class SecSendCmdTelResponse:
    reply: SecwaveReplyState | None


SecTelegram = SecCommandTelegram
