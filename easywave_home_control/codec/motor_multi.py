"""Dual and quadruple EWB motor control state parsing and encoding."""

from __future__ import annotations

from dataclasses import dataclass

from ..protocols.rx11_rx2x.protocol import DeviceType
from .common import (
    StateDirection,
    encode_state_word,
    get_bits,
    set_bits,
    state_word,
)
from .exceptions import UnknownModeError
from . import motor as single_motor
from .states import (
    DeviceFeaturesState,
    MotorActivity,
    MotorMoveCommand,
    MotorSummaryChannelState,
    MultiMotorFullState,
    MultiMotorMoveCommand,
    MultiMotorStoredPositionsState,
    MultiMotorSummaryState,
    MultiMotorTerraceCommand,
    MOTOR_NO_CHANGE,
    EwbState,
)

MODE_SUMMARY = 0
MODE_FEATURES = 7


@dataclass(frozen=True)
class _MotorChannelLayout:
    index: int
    activity_high: int
    activity_low: int
    slats_bit: int
    full_mode: int
    terrace_mode: int
    stored_mode: int


DUAL_LAYOUT = (
    _MotorChannelLayout(1, 31, 25, 24, 2, 2, 6),
    _MotorChannelLayout(2, 23, 17, 16, 10, 10, 14),
)

QUAD_LAYOUT = (
    _MotorChannelLayout(1, 31, 25, 24, 2, 2, 6),
    _MotorChannelLayout(2, 23, 17, 16, 10, 10, 14),
    _MotorChannelLayout(3, 15, 9, 8, 18, 18, 22),
    _MotorChannelLayout(4, 7, 1, 0, 26, 26, 30),
)


def _device_type(channel_count: int) -> DeviceType:
    return DeviceType.EWB_DT_DUAL_MOTOR if channel_count == 2 else DeviceType.EWB_DT_QUAD_MOTOR


def _layout_for_mode(mode: int, layouts: tuple[_MotorChannelLayout, ...]) -> _MotorChannelLayout | None:
    for layout in layouts:
        if mode in (layout.full_mode, layout.terrace_mode, layout.stored_mode):
            return layout
    return None


def parse_dual(
    mode: int,
    state_bytes: bytes,
    *,
    direction: StateDirection = StateDirection.FROM_DEVICE,
) -> EwbState:
    return _parse(DUAL_LAYOUT, mode, state_bytes, direction=direction)


def encode_dual(
    mode: int,
    state: EwbState,
    *,
    direction: StateDirection = StateDirection.TO_DEVICE,
) -> bytes:
    return _encode(DUAL_LAYOUT, mode, state, direction=direction)


def parse_quad(
    mode: int,
    state_bytes: bytes,
    *,
    direction: StateDirection = StateDirection.FROM_DEVICE,
) -> EwbState:
    return _parse(QUAD_LAYOUT, mode, state_bytes, direction=direction)


def encode_quad(
    mode: int,
    state: EwbState,
    *,
    direction: StateDirection = StateDirection.TO_DEVICE,
) -> bytes:
    return _encode(QUAD_LAYOUT, mode, state, direction=direction)


def _parse_summary(
    layouts: tuple[_MotorChannelLayout, ...], word: int
) -> MultiMotorSummaryState:
    channels: list[MotorSummaryChannelState] = []
    for layout in layouts:
        activity_raw = get_bits(word, layout.activity_high, layout.activity_low)
        try:
            activity: MotorActivity | int = MotorActivity(activity_raw)
        except ValueError:
            activity = activity_raw
        channels.append(
            MotorSummaryChannelState(
                channel=layout.index,
                activity=activity,
                slats_tilted=bool((word >> layout.slats_bit) & 1),
            )
        )
    return MultiMotorSummaryState(channels=tuple(channels))


def _parse(
    layouts: tuple[_MotorChannelLayout, ...],
    mode: int,
    state_bytes: bytes,
    *,
    direction: StateDirection,
) -> EwbState:
    word = state_word(state_bytes)
    device_type = _device_type(len(layouts))

    if mode == MODE_SUMMARY:
        if direction == StateDirection.TO_DEVICE:
            channels: list[tuple[int, MotorMoveCommand | None]] = []
            for layout in layouts:
                value = get_bits(word, layout.activity_high, layout.activity_low)
                if value == MOTOR_NO_CHANGE:
                    channels.append((layout.index, None))
                    continue
                tilt = bool((word >> layout.slats_bit) & 1)
                if value <= 100:
                    channels.append(
                        (
                            layout.index,
                            MotorMoveCommand(command=value, position=value, tilt_after_move=tilt),
                        )
                    )
                else:
                    channels.append(
                        (layout.index, MotorMoveCommand(command=value, tilt_after_move=tilt))
                    )
            return MultiMotorMoveCommand(channels=tuple(channels))
        return _parse_summary(layouts, word)

    layout = _layout_for_mode(mode, layouts)
    if layout is None:
        if mode == MODE_FEATURES:
            return DeviceFeaturesState(features=word)
        raise UnknownModeError(mode, device_type, direction=direction.name)

    if mode == layout.full_mode:
        from .states import MotorFullState

        parsed = single_motor.parse(single_motor.MODE_FULL, state_bytes, direction=direction)
        if not isinstance(parsed, MotorFullState):
            raise TypeError(f"Expected MotorFullState from motor parser, got {type(parsed)}")
        return MultiMotorFullState(channel=layout.index, state=parsed)

    if mode == layout.terrace_mode:
        enabled = bool(get_bits(word, 31, 24))
        return MultiMotorTerraceCommand(channel=layout.index, enabled=enabled)

    if mode == layout.stored_mode:
        from .states import MotorStoredPositionsState

        stored = single_motor.parse(
            single_motor.MODE_STORED_POSITIONS, state_bytes, direction=direction
        )
        if not isinstance(stored, MotorStoredPositionsState):
            raise TypeError(f"Expected MotorStoredPositionsState, got {type(stored)}")
        return MultiMotorStoredPositionsState(channel=layout.index, positions=stored)

    raise UnknownModeError(mode, device_type, direction=direction.name)


def _encode(
    layouts: tuple[_MotorChannelLayout, ...],
    mode: int,
    state: EwbState,
    *,
    direction: StateDirection,
) -> bytes:
    device_type = _device_type(len(layouts))

    if mode == MODE_SUMMARY:
        if direction == StateDirection.TO_DEVICE and isinstance(state, MultiMotorMoveCommand):
            word = 0
            command_map = dict(state.channels)
            for layout in layouts:
                command = command_map.get(layout.index)
                if command is None:
                    word = set_bits(word, layout.activity_high, layout.activity_low, MOTOR_NO_CHANGE)
                    continue
                value = command.position if command.position is not None else int(command.command)
                word = set_bits(word, layout.activity_high, layout.activity_low, value)
                if command.tilt_after_move:
                    word = set_bits(word, layout.slats_bit, layout.slats_bit, 1)
            return encode_state_word(word)
        if isinstance(state, MultiMotorSummaryState):
            word = 0
            summary_map = {item.channel: item for item in state.channels}
            for layout in layouts:
                item = summary_map[layout.index]
                word = set_bits(word, layout.activity_high, layout.activity_low, int(item.activity))
                if item.slats_tilted:
                    word = set_bits(word, layout.slats_bit, layout.slats_bit, 1)
            return encode_state_word(word)
        raise TypeError(f"Unexpected multi motor summary state: {type(state)}")

    layout = _layout_for_mode(mode, layouts)
    if layout is not None and mode == layout.full_mode and isinstance(state, MultiMotorFullState):
        return single_motor.encode(single_motor.MODE_FULL, state.state, direction=direction)
    if layout is not None and mode == layout.terrace_mode and isinstance(state, MultiMotorTerraceCommand):
        return encode_state_word(set_bits(0, 31, 24, 1 if state.enabled else 0))
    if layout is not None and mode == layout.stored_mode and isinstance(state, MultiMotorStoredPositionsState):
        return single_motor.encode(single_motor.MODE_STORED_POSITIONS, state.positions, direction=direction)
    if mode == MODE_FEATURES and isinstance(state, DeviceFeaturesState):
        return encode_state_word(state.features)

    raise UnknownModeError(mode, device_type, direction=direction.name)
