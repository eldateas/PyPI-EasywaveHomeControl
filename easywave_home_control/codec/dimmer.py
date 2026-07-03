"""EWB dimmer state parsing and encoding."""

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
    DimmerFeaturesState,
    DimmerLevelCommand,
    DimmerLevelState,
    DimmerPhaseControlState,
    EwbState,
    TimerDuration,
)

MODE_LEVEL = 0
MODE_PHASE_CONTROL = 6
MODE_FEATURES = 7


def _remaining_from_word(word: int) -> TimerDuration | None:
    remaining = parse_timer_high_low(word, 15, 12, 11, 4)
    if remaining.mantissa == 0 and remaining.exponent == 0:
        return None
    return remaining


def parse(
    mode: int,
    state_bytes: bytes,
    *,
    direction: StateDirection = StateDirection.FROM_DEVICE,
) -> EwbState:
    word = state_word(state_bytes)
    if mode == MODE_LEVEL:
        if direction == StateDirection.TO_DEVICE:
            duration = _remaining_from_word(word)
            return DimmerLevelCommand(
                target_level=get_bits(word, 31, 24),
                duration=duration,
            )
        return DimmerLevelState(
            target_level=get_bits(word, 31, 24),
            current_level=get_bits(word, 23, 16),
            remaining=_remaining_from_word(word),
        )
    if mode == MODE_PHASE_CONTROL:
        return DimmerPhaseControlState(phase_control_type=get_bits(word, 31, 24))
    if mode == MODE_FEATURES:
        return DimmerFeaturesState(features=word)
    raise UnknownModeError(mode, DeviceType.EWB_DT_DIMMER, direction=direction.name)


def encode(
    mode: int,
    state: EwbState,
    *,
    direction: StateDirection = StateDirection.TO_DEVICE,
) -> bytes:
    word = 0
    if mode == MODE_LEVEL:
        if direction == StateDirection.TO_DEVICE and isinstance(state, DimmerLevelCommand):
            word = set_bits(word, 31, 24, state.target_level)
            if state.duration is not None:
                word = encode_timer_high_low(word, state.duration, 15, 12, 11, 4)
        elif isinstance(state, DimmerLevelState):
            word = set_bits(word, 31, 24, state.target_level)
            word = set_bits(word, 23, 16, state.current_level)
            if state.remaining is not None:
                word = encode_timer_high_low(word, state.remaining, 15, 12, 11, 4)
        else:
            raise TypeError(f"Expected DimmerLevelCommand or DimmerLevelState, got {type(state)}")
    elif mode == MODE_PHASE_CONTROL and isinstance(state, DimmerPhaseControlState):
        word = set_bits(word, 31, 24, state.phase_control_type)
    elif mode == MODE_FEATURES and isinstance(state, DimmerFeaturesState):
        word = state.features
    else:
        raise UnknownModeError(mode, DeviceType.EWB_DT_DIMMER, direction=direction.name)
    return encode_state_word(word)
