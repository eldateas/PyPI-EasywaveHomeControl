"""Central dispatch for EWB state parsing and encoding."""

from __future__ import annotations

from ..protocols.rx11_rx2x.protocol import DeviceType
from . import dimmer, motor, motor_multi, switch, switch_multi
from .common import StateDirection
from .exceptions import UnknownModeError
from .states import EwbState

_PARSERS = {
    DeviceType.EWB_DT_SWITCH: switch.parse,
    DeviceType.EWB_DT_DUAL_SWITCH: switch_multi.parse_dual,
    DeviceType.EWB_DT_QUAD_SWITCH: switch_multi.parse_quad,
    DeviceType.EWB_DT_DIMMER: dimmer.parse,
    DeviceType.EWB_DT_MOTOR: motor.parse,
    DeviceType.EWB_DT_DUAL_MOTOR: motor_multi.parse_dual,
    DeviceType.EWB_DT_QUAD_MOTOR: motor_multi.parse_quad,
}

_ENCODERS = {
    DeviceType.EWB_DT_SWITCH: switch.encode,
    DeviceType.EWB_DT_DUAL_SWITCH: switch_multi.encode_dual,
    DeviceType.EWB_DT_QUAD_SWITCH: switch_multi.encode_quad,
    DeviceType.EWB_DT_DIMMER: dimmer.encode,
    DeviceType.EWB_DT_MOTOR: motor.encode,
    DeviceType.EWB_DT_DUAL_MOTOR: motor_multi.encode_dual,
    DeviceType.EWB_DT_QUAD_MOTOR: motor_multi.encode_quad,
}


def _normalize_device_type(device_type: int | DeviceType) -> DeviceType:
    try:
        return DeviceType(device_type)
    except ValueError as exc:
        raise UnknownModeError(0, int(device_type)) from exc


def parse_ewb_state(
    device_type: int | DeviceType,
    mode: int,
    state_bytes: bytes,
    *,
    direction: StateDirection = StateDirection.FROM_DEVICE,
) -> EwbState:
    """Decode a 4-byte EWB state word for query, change, or RCV notifications."""
    normalized = _normalize_device_type(device_type)
    parser = _PARSERS.get(normalized)
    if parser is None:
        raise UnknownModeError(mode, int(normalized), direction=direction.name)
    return parser(mode, state_bytes, direction=direction)


def encode_ewb_state(
    device_type: int | DeviceType,
    mode: int,
    state: EwbState,
    *,
    direction: StateDirection = StateDirection.TO_DEVICE,
) -> bytes:
    """Encode a typed state object into a 4-byte EWB state word."""
    normalized = _normalize_device_type(device_type)
    encoder = _ENCODERS.get(normalized)
    if encoder is None:
        raise UnknownModeError(mode, int(normalized), direction=direction.name)
    return encoder(mode, state, direction=direction)
