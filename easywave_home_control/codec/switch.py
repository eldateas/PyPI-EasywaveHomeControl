"""Single EWB switch state parsing and encoding."""

from __future__ import annotations

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
    SwitchChangeCommand,
    SwitchDefaultDurationState,
    SwitchDesiredAction,
    SwitchOnOffState,
    SwitchPosition,
    SwitchTimerCommand,
    SwitchTimerState,
    EwbState,
)

MODE_ON_OFF = 0
MODE_TIMER = 1
MODE_DEFAULT_DURATION = 6
MODE_FEATURES = 7


def parse(
    mode: int,
    state_bytes: bytes,
    *,
    direction: StateDirection = StateDirection.FROM_DEVICE,
) -> EwbState:
    word = state_word(state_bytes)
    if mode == MODE_ON_OFF:
        if direction == StateDirection.TO_DEVICE:
            action_value = get_bits(word, 26, 24)
            return SwitchChangeCommand(action=SwitchDesiredAction(action_value))
        return SwitchOnOffState(
            pulse_counter=get_bits(word, 31, 27),
            position=SwitchPosition(get_bits(word, 26, 24)),
        )
    if mode == MODE_TIMER:
        if direction == StateDirection.TO_DEVICE:
            return SwitchTimerCommand(
                duration=parse_timer_high_low(word, 31, 28, 27, 20),
                switch_off_warning=bool(word & 1),
            )
        return SwitchTimerState(
            started_duration=parse_timer_high_low(word, 31, 28, 27, 20),
            remaining=parse_timer_high_low(word, 19, 16, 15, 8),
            default_duration=bool((word >> 1) & 1),
            switch_off_warning=bool(word & 1),
        )
    if mode == MODE_DEFAULT_DURATION:
        return SwitchDefaultDurationState(
            default_duration=parse_timer_high_low(word, 31, 28, 27, 20),
            switch_off_warning=bool(word & 1),
        )
    if mode == MODE_FEATURES:
        return DeviceFeaturesState(features=word)
    raise UnknownModeError(mode, DeviceType.EWB_DT_SWITCH, direction=direction.name)


def encode(
    mode: int,
    state: EwbState,
    *,
    direction: StateDirection = StateDirection.TO_DEVICE,
) -> bytes:
    word = 0
    if mode == MODE_ON_OFF:
        if direction == StateDirection.TO_DEVICE and isinstance(state, SwitchChangeCommand):
            word = set_bits(word, 26, 24, int(state.action))
        elif isinstance(state, SwitchOnOffState):
            word = set_bits(word, 31, 27, state.pulse_counter)
            word = set_bits(word, 26, 24, int(state.position))
        else:
            raise TypeError(f"Expected SwitchChangeCommand or SwitchOnOffState, got {type(state)}")
    elif mode == MODE_TIMER:
        if direction == StateDirection.TO_DEVICE and isinstance(state, SwitchTimerCommand):
            word = encode_timer_high_low(word, state.duration, 31, 28, 27, 20)
            if state.switch_off_warning:
                word |= 1
        elif isinstance(state, SwitchTimerState):
            word = encode_timer_high_low(word, state.started_duration, 31, 28, 27, 20)
            word = encode_timer_high_low(word, state.remaining, 19, 16, 15, 8)
            if state.default_duration:
                word |= 1 << 1
            if state.switch_off_warning:
                word |= 1
        else:
            raise TypeError(f"Expected SwitchTimerCommand or SwitchTimerState, got {type(state)}")
    elif mode == MODE_DEFAULT_DURATION and isinstance(state, SwitchDefaultDurationState):
        word = encode_timer_high_low(word, state.default_duration, 31, 28, 27, 20)
        if state.switch_off_warning:
            word |= 1
    elif mode == MODE_FEATURES and isinstance(state, DeviceFeaturesState):
        word = state.features
    else:
        raise UnknownModeError(mode, DeviceType.EWB_DT_SWITCH, direction=direction.name)
    return encode_state_word(word)
