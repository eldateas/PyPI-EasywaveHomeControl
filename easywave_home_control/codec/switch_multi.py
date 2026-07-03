"""Dual and quadruple EWB switch state parsing and encoding."""

from __future__ import annotations

from dataclasses import dataclass

from ..protocols.rx11_rx2x.protocol import DeviceType
from .common import (
    StateDirection,
    encode_state_word,
    encode_timer_high_low,
    get_bits,
    parse_timer_high_low,
    set_bits,
    state_word,
)
from .exceptions import UnknownModeError
from .states import (
    DeviceFeaturesState,
    MultiSwitchChangeCommand,
    MultiSwitchDefaultDurationState,
    MultiSwitchOnOffState,
    MultiSwitchTimerCommand,
    MultiSwitchTimerState,
    SwitchChannelOnOffState,
    SwitchDesiredAction,
    SwitchPosition,
    EwbState,
)

MODE_ON_OFF = 0
MODE_FEATURES = 7


@dataclass(frozen=True)
class _ChannelLayout:
    index: int
    counter_high: int
    counter_low: int
    position_high: int
    position_low: int
    timer_mode: int
    default_duration_mode: int


DUAL_LAYOUT = (
    _ChannelLayout(1, 31, 27, 26, 24, 1, 6),
    _ChannelLayout(2, 23, 19, 18, 16, 9, 14),
)

QUAD_LAYOUT = (
    _ChannelLayout(1, 31, 27, 26, 24, 1, 6),
    _ChannelLayout(2, 23, 19, 18, 16, 9, 14),
    _ChannelLayout(3, 15, 11, 10, 8, 17, 22),
    _ChannelLayout(4, 7, 3, 2, 0, 25, 30),
)

DESIRED_REMAIN = 0
DESIRED_OFF = 1
DESIRED_ON = 2
DESIRED_ON_TIMER = 3


def _device_type(channel_count: int) -> DeviceType:
    return DeviceType.EWB_DT_DUAL_SWITCH if channel_count == 2 else DeviceType.EWB_DT_QUAD_SWITCH


def _layout_for_mode(mode: int, layouts: tuple[_ChannelLayout, ...]) -> _ChannelLayout | None:
    for layout in layouts:
        if mode in (layout.timer_mode, layout.default_duration_mode):
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


def _parse(
    layouts: tuple[_ChannelLayout, ...],
    mode: int,
    state_bytes: bytes,
    *,
    direction: StateDirection,
) -> EwbState:
    word = state_word(state_bytes)
    device_type = _device_type(len(layouts))

    if mode == MODE_ON_OFF:
        if direction == StateDirection.TO_DEVICE:
            channels: list[tuple[int, SwitchDesiredAction | None]] = []
            for layout in layouts:
                value = get_bits(word, layout.position_high, layout.position_low)
                if value == DESIRED_REMAIN:
                    channels.append((layout.index, None))
                else:
                    channels.append((layout.index, SwitchDesiredAction(value)))
            return MultiSwitchChangeCommand(channels=tuple(channels))

        channel_states = tuple(
            SwitchChannelOnOffState(
                channel=layout.index,
                pulse_counter=get_bits(word, layout.counter_high, layout.counter_low),
                position=SwitchPosition(get_bits(word, layout.position_high, layout.position_low)),
            )
            for layout in layouts
        )
        return MultiSwitchOnOffState(channels=channel_states)

    layout = _layout_for_mode(mode, layouts)
    if layout is not None and mode == layout.timer_mode:
        if direction == StateDirection.TO_DEVICE:
            return MultiSwitchTimerCommand(
                channel=layout.index,
                duration=parse_timer_high_low(word, 31, 28, 27, 20),
                switch_off_warning=bool(word & 1),
            )
        return MultiSwitchTimerState(
            channel=layout.index,
            started_duration=parse_timer_high_low(word, 31, 28, 27, 20),
            remaining=parse_timer_high_low(word, 19, 16, 15, 8),
            default_duration=bool((word >> 1) & 1),
            switch_off_warning=bool(word & 1),
        )

    if layout is not None and mode == layout.default_duration_mode:
        return MultiSwitchDefaultDurationState(
            channel=layout.index,
            default_duration=parse_timer_high_low(word, 31, 28, 27, 20),
            switch_off_warning=bool(word & 1),
        )

    if mode == MODE_FEATURES:
        return DeviceFeaturesState(features=word)

    raise UnknownModeError(mode, device_type, direction=direction.name)


def _encode(
    layouts: tuple[_ChannelLayout, ...],
    mode: int,
    state: EwbState,
    *,
    direction: StateDirection,
) -> bytes:
    word = 0
    device_type = _device_type(len(layouts))

    if mode == MODE_ON_OFF:
        if direction == StateDirection.TO_DEVICE and isinstance(state, MultiSwitchChangeCommand):
            action_map = dict(state.channels)
            for layout in layouts:
                action = action_map.get(layout.index)
                if action is None:
                    value = DESIRED_REMAIN
                else:
                    value = int(action)
                word = set_bits(word, layout.position_high, layout.position_low, value)
        elif isinstance(state, MultiSwitchOnOffState):
            channel_map = {item.channel: item for item in state.channels}
            for layout in layouts:
                item = channel_map[layout.index]
                word = set_bits(word, layout.counter_high, layout.counter_low, item.pulse_counter)
                word = set_bits(word, layout.position_high, layout.position_low, int(item.position))
        else:
            raise TypeError(f"Unexpected state type for multi switch mode 0: {type(state)}")
    else:
        layout = _layout_for_mode(mode, layouts)
        if layout is not None and mode == layout.timer_mode:
            if direction == StateDirection.TO_DEVICE and isinstance(state, MultiSwitchTimerCommand):
                word = encode_timer_high_low(word, state.duration, 31, 28, 27, 20)
                if state.switch_off_warning:
                    word |= 1
            elif isinstance(state, MultiSwitchTimerState):
                word = encode_timer_high_low(word, state.started_duration, 31, 28, 27, 20)
                word = encode_timer_high_low(word, state.remaining, 19, 16, 15, 8)
                if state.default_duration:
                    word |= 1 << 1
                if state.switch_off_warning:
                    word |= 1
            else:
                raise TypeError(f"Unexpected state type for timer mode {mode}: {type(state)}")
        elif layout is not None and mode == layout.default_duration_mode:
            if not isinstance(state, MultiSwitchDefaultDurationState):
                raise TypeError(f"Expected MultiSwitchDefaultDurationState, got {type(state)}")
            word = encode_timer_high_low(word, state.default_duration, 31, 28, 27, 20)
            if state.switch_off_warning:
                word |= 1
        elif mode == MODE_FEATURES and isinstance(state, DeviceFeaturesState):
            word = state.features
        else:
            raise UnknownModeError(mode, device_type, direction=direction.name)

    return encode_state_word(word)
