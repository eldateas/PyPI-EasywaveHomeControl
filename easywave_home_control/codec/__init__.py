"""EWB state and telegram codec layer."""

from __future__ import annotations

from .common import StateDirection, TimerDuration
from .dispatch import encode_ewb_state, parse_ewb_state
from .events import (
    ButtonFunction,
    ButtonPushEvent,
    ButtonReleaseEvent,
    EasywaveButton,
    EwbRcvEvent,
    EwbStateChangeEvent,
    SensorTelegramEvent,
    TransmitterLearnAbortEvent,
    TransmitterLearnSuccessEvent,
    TransmitterRemoveSuccessEvent,
    UnknownEwbRcvEvent,
)
from .exceptions import CodecError, InvalidPayloadError, UnknownModeError
from .sensors import (
    BatteryLevel,
    MeasurementType,
    SensorLearnPayload,
    SensorMeasurementPayload,
    SensorPayloadFormat,
    parse_sensor_payload,
)
from .states import (
    DimmerLevelCommand,
    DimmerLevelState,
    EwbState,
    MotorActivity,
    MotorCommand,
    MotorFullState,
    MotorMoveCommand,
    SwitchChangeCommand,
    SwitchDesiredAction,
    SwitchOnOffState,
    SwitchPosition,
    SwitchTimerState,
)
from .telegram import parse_ewb_rcv, parse_ewb_rcv_result, parse_ew_rcv_ex_result

from . import easywave, secwave

__all__ = [
    "ButtonFunction",
    "ButtonPushEvent",
    "ButtonReleaseEvent",
    "CodecError",
    "DimmerLevelCommand",
    "DimmerLevelState",
    "EasywaveButton",
    "EwbRcvEvent",
    "EwbState",
    "EwbStateChangeEvent",
    "InvalidPayloadError",
    "BatteryLevel",
    "MeasurementType",
    "MotorActivity",
    "MotorCommand",
    "MotorFullState",
    "MotorMoveCommand",
    "SensorLearnPayload",
    "SensorMeasurementPayload",
    "SensorPayloadFormat",
    "SensorTelegramEvent",
    "StateDirection",
    "SwitchChangeCommand",
    "SwitchDesiredAction",
    "SwitchOnOffState",
    "SwitchPosition",
    "SwitchTimerState",
    "TimerDuration",
    "TransmitterLearnAbortEvent",
    "TransmitterLearnSuccessEvent",
    "TransmitterRemoveSuccessEvent",
    "UnknownEwbRcvEvent",
    "UnknownModeError",
    "encode_ewb_state",
    "easywave",
    "parse_ewb_rcv",
    "parse_ewb_rcv_result",
    "parse_ew_rcv_ex_result",
    "parse_ewb_state",
    "parse_sensor_payload",
    "secwave",
]
