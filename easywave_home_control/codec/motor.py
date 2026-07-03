"""Single EWB motor control state parsing and encoding."""

from __future__ import annotations

from ..protocols.rx11_rx2x.protocol import DeviceType
from .common import (
    StateDirection,
    encode_state_word,
    get_bits,
    set_bits,
    state_word,
)
from .exceptions import UnknownModeError
from .states import (
    DeviceFeaturesState,
    MotorActivity,
    MotorCommand,
    MotorFeaturesState,
    MotorFullState,
    MotorMoveCommand,
    MotorStoredPositionsState,
    MotorTerraceCommand,
    MOTOR_POSITION_UNKNOWN,
    EwbState,
)


MODE_FULL = 0
MODE_TERRACE = 2
MODE_STORED_POSITIONS = 6
MODE_FEATURES = 7


def _position_value(value: int) -> int | None:
    if value >= 127:
        return None
    if value == MOTOR_POSITION_UNKNOWN:
        return None
    return value


def _parse_full(word: int) -> MotorFullState:
    activity_raw = get_bits(word, 31, 25)
    try:
        activity: MotorActivity | int = MotorActivity(activity_raw)
    except ValueError:
        activity = activity_raw
    return MotorFullState(
        activity=activity,
        current_position=_position_value(get_bits(word, 23, 17)),
        target_position=_position_value(get_bits(word, 15, 9)),
        slats_tilted=bool((word >> 16) & 1),
        tilt_after_move=bool((word >> 8) & 1),
        runtime_measured=bool((word >> 7) & 1),
        tilt_measured=bool((word >> 6) & 1),
        terrace_on=bool((word >> 2) & 1),
        stored_position_slot=get_bits(word, 1, 0),
    )


def parse(
    mode: int,
    state_bytes: bytes,
    *,
    direction: StateDirection = StateDirection.FROM_DEVICE,
) -> EwbState:
    word = state_word(state_bytes)
    if mode == MODE_FULL:
        if direction == StateDirection.TO_DEVICE:
            command_raw = get_bits(word, 31, 25)
            try:
                command: MotorCommand | int = MotorCommand(command_raw)
            except ValueError:
                command = command_raw
            position = _position_value(command_raw)
            if command_raw <= 100:
                return MotorMoveCommand(
                    command=command_raw,
                    position=position,
                    tilt_after_move=bool((word >> 24) & 1),
                )
            return MotorMoveCommand(
                command=command,
                tilt_after_move=bool((word >> 24) & 1),
            )
        return _parse_full(word)
    if mode == MODE_TERRACE:
        return MotorTerraceCommand(enabled=bool(get_bits(word, 31, 24)))
    if mode == MODE_STORED_POSITIONS:
        return MotorStoredPositionsState(
            position1=_position_value(get_bits(word, 31, 25)),
            position2=_position_value(get_bits(word, 23, 17)),
            position3=_position_value(get_bits(word, 15, 9)),
        )
    if mode == MODE_FEATURES:
        return MotorFeaturesState(features=word)
    raise UnknownModeError(mode, DeviceType.EWB_DT_MOTOR, direction=direction.name)


def encode(
    mode: int,
    state: EwbState,
    *,
    direction: StateDirection = StateDirection.TO_DEVICE,
) -> bytes:
    word = 0
    if mode == MODE_FULL:
        if direction == StateDirection.TO_DEVICE and isinstance(state, MotorMoveCommand):
            command_value = int(state.command)
            if state.position is not None and command_value <= 100:
                command_value = state.position
            word = set_bits(word, 31, 25, command_value)
            if state.tilt_after_move:
                word = set_bits(word, 24, 24, 1)
        elif isinstance(state, MotorFullState):
            word = set_bits(word, 31, 25, int(state.activity))
            if state.current_position is not None:
                word = set_bits(word, 23, 17, state.current_position)
            else:
                word = set_bits(word, 23, 17, MOTOR_POSITION_UNKNOWN)
            if state.slats_tilted:
                word = set_bits(word, 16, 16, 1)
            if state.target_position is not None:
                word = set_bits(word, 15, 9, state.target_position)
            else:
                word = set_bits(word, 15, 9, MOTOR_POSITION_UNKNOWN)
            if state.tilt_after_move:
                word = set_bits(word, 8, 8, 1)
            if state.runtime_measured:
                word = set_bits(word, 7, 7, 1)
            if state.tilt_measured:
                word = set_bits(word, 6, 6, 1)
            if state.terrace_on:
                word = set_bits(word, 2, 2, 1)
            word = set_bits(word, 1, 0, state.stored_position_slot)
        else:
            raise TypeError(f"Expected MotorMoveCommand or MotorFullState, got {type(state)}")
    elif mode == MODE_TERRACE and isinstance(state, MotorTerraceCommand):
        word = set_bits(word, 31, 24, 1 if state.enabled else 0)
    elif mode == MODE_STORED_POSITIONS and isinstance(state, MotorStoredPositionsState):
        if state.position1 is not None:
            word = set_bits(word, 31, 25, state.position1)
        if state.position2 is not None:
            word = set_bits(word, 23, 17, state.position2)
        if state.position3 is not None:
            word = set_bits(word, 15, 9, state.position3)
    elif mode == MODE_FEATURES and isinstance(state, MotorFeaturesState):
        word = state.features
    else:
        raise UnknownModeError(mode, DeviceType.EWB_DT_MOTOR, direction=direction.name)
    return encode_state_word(word)
