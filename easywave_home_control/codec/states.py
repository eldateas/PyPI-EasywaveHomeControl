"""Typed EWB state dataclasses shared across device codecs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Union

from .common import TimerDuration


class SwitchPosition(IntEnum):
    OFF = 1
    ON = 2
    ON_TIMER = 3
    ON_LOGIC = 5


class SwitchDesiredAction(IntEnum):
    OFF = 1
    ON = 2
    ON_WITH_DEFAULT_TIMER = 3


@dataclass(frozen=True)
class SwitchOnOffState:
    pulse_counter: int
    position: SwitchPosition


@dataclass(frozen=True)
class SwitchChangeCommand:
    action: SwitchDesiredAction


@dataclass(frozen=True)
class SwitchTimerState:
    started_duration: TimerDuration
    remaining: TimerDuration
    default_duration: bool
    switch_off_warning: bool


@dataclass(frozen=True)
class SwitchTimerCommand:
    duration: TimerDuration
    switch_off_warning: bool


@dataclass(frozen=True)
class SwitchDefaultDurationState:
    default_duration: TimerDuration
    switch_off_warning: bool


@dataclass(frozen=True)
class SwitchFeaturesState:
    features: int


@dataclass(frozen=True)
class SwitchChannelOnOffState:
    channel: int
    pulse_counter: int
    position: SwitchPosition


@dataclass(frozen=True)
class MultiSwitchOnOffState:
    channels: tuple[SwitchChannelOnOffState, ...]


@dataclass(frozen=True)
class MultiSwitchChangeCommand:
    channels: tuple[tuple[int, SwitchDesiredAction | None], ...]


@dataclass(frozen=True)
class MultiSwitchTimerState:
    channel: int
    started_duration: TimerDuration
    remaining: TimerDuration
    default_duration: bool
    switch_off_warning: bool


@dataclass(frozen=True)
class MultiSwitchTimerCommand:
    channel: int
    duration: TimerDuration
    switch_off_warning: bool


@dataclass(frozen=True)
class MultiSwitchDefaultDurationState:
    channel: int
    default_duration: TimerDuration
    switch_off_warning: bool


@dataclass(frozen=True)
class DimmerLevelState:
    target_level: int
    current_level: int
    remaining: TimerDuration | None


@dataclass(frozen=True)
class DimmerLevelCommand:
    target_level: int
    duration: TimerDuration | None


@dataclass(frozen=True)
class DimmerPhaseControlState:
    phase_control_type: int


@dataclass(frozen=True)
class DimmerFeaturesState:
    features: int


class MotorActivity(IntEnum):
    RUNTIME_MEASUREMENT = 117
    TILT_MEASUREMENT = 118
    STOPPED_TERRACE = 119
    OPENING_RUNTIME = 120
    CLOSING_RUNTIME = 121
    OPENING_120S = 122
    CLOSING_120S = 123
    OPENING_TO_POSITION = 124
    CLOSING_TO_POSITION = 125
    STOPPED = 126


class MotorCommand(IntEnum):
    STOP = 126
    STOP_AND_TILT = 119
    OPEN_RUNTIME = 120
    CLOSE_RUNTIME = 121
    OPEN_120S = 122
    CLOSE_120S = 123


MOTOR_POSITION_UNKNOWN = 126
MOTOR_NO_CHANGE = 127


@dataclass(frozen=True)
class MotorFullState:
    activity: MotorActivity | int
    current_position: int | None
    target_position: int | None
    slats_tilted: bool
    tilt_after_move: bool
    runtime_measured: bool
    tilt_measured: bool
    terrace_on: bool
    stored_position_slot: int


@dataclass(frozen=True)
class MotorMoveCommand:
    command: MotorCommand | int
    position: int | None = None
    tilt_after_move: bool = False


@dataclass(frozen=True)
class MotorTerraceCommand:
    enabled: bool


@dataclass(frozen=True)
class MotorStoredPositionsState:
    position1: int | None
    position2: int | None
    position3: int | None


@dataclass(frozen=True)
class MotorFeaturesState:
    features: int


@dataclass(frozen=True)
class MotorSummaryChannelState:
    channel: int
    activity: MotorActivity | int
    slats_tilted: bool
    # Mode 0 uses the same 7-bit field for position (0-100) or activity (>=117).
    position: int | None = None


@dataclass(frozen=True)
class MultiMotorSummaryState:
    channels: tuple[MotorSummaryChannelState, ...]


@dataclass(frozen=True)
class MultiMotorMoveCommand:
    channels: tuple[tuple[int, MotorMoveCommand | None], ...]


@dataclass(frozen=True)
class MultiMotorTerraceCommand:
    channel: int
    enabled: bool


@dataclass(frozen=True)
class MultiMotorFullState:
    channel: int
    state: MotorFullState


@dataclass(frozen=True)
class MultiMotorStoredPositionsState:
    channel: int
    positions: MotorStoredPositionsState


@dataclass(frozen=True)
class DeviceFeaturesState:
    features: int


EwbState = Union[
    SwitchOnOffState,
    SwitchChangeCommand,
    SwitchTimerState,
    SwitchTimerCommand,
    SwitchDefaultDurationState,
    SwitchFeaturesState,
    MultiSwitchOnOffState,
    MultiSwitchChangeCommand,
    MultiSwitchTimerState,
    MultiSwitchTimerCommand,
    MultiSwitchDefaultDurationState,
    DimmerLevelState,
    DimmerLevelCommand,
    DimmerPhaseControlState,
    DimmerFeaturesState,
    MotorFullState,
    MotorMoveCommand,
    MotorTerraceCommand,
    MotorStoredPositionsState,
    MotorFeaturesState,
    MultiMotorSummaryState,
    MultiMotorMoveCommand,
    MultiMotorTerraceCommand,
    MultiMotorFullState,
    MultiMotorStoredPositionsState,
    DeviceFeaturesState,
]
