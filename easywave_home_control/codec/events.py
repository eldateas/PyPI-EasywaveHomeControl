"""Typed events decoded from EWB_RCV telegrams."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Union

from .sensors import SensorPayload
from .states import EwbState


class EasywaveButton(IntEnum):
    A = 0
    B = 1
    C = 2
    D = 3


class ButtonFunction(IntEnum):
    DEFAULT = 0
    REMOTE_LEARN_DELETE = 1
    REMOTE_LEARN_ADD = 2
    REMOTE_LEARN_RESET = 3
    REMOTE_LEARN_TIMER = 4
    EMULATED_HOLD = 5
    EMULATED_RELEASE = 6
    LOW_BATTERY = 32  # entire byte is 0x80


@dataclass(frozen=True)
class ButtonPushEvent:
    transmitter_serial: bytes
    button: EasywaveButton
    function: ButtonFunction
    should_ignore: bool


@dataclass(frozen=True)
class ButtonReleaseEvent:
    transmitter_serial: bytes


@dataclass(frozen=True)
class EwbStateChangeEvent:
    receiver_serial: bytes
    mode: int
    state: EwbState


@dataclass(frozen=True)
class SensorTelegramEvent:
    sensor_serial: bytes
    payload: SensorPayload


@dataclass(frozen=True)
class TransmitterLearnAbortEvent:
    receiver_serial: bytes


@dataclass(frozen=True)
class TransmitterLearnSuccessEvent:
    receiver_serial: bytes


@dataclass(frozen=True)
class TransmitterRemoveSuccessEvent:
    receiver_serial: bytes


@dataclass(frozen=True)
class UnknownEwbRcvEvent:
    info_type: int
    serial: bytes
    info_data: bytes


EwbRcvEvent = Union[
    ButtonPushEvent,
    ButtonReleaseEvent,
    EwbStateChangeEvent,
    SensorTelegramEvent,
    TransmitterLearnAbortEvent,
    TransmitterLearnSuccessEvent,
    TransmitterRemoveSuccessEvent,
    UnknownEwbRcvEvent,
]
