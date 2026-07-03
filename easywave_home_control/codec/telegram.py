"""EWB_RCV telegram parsing."""

from __future__ import annotations

from ..protocols.rx11_rx2x.protocol import InfoType
from .common import StateDirection
from .dispatch import parse_ewb_state
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
from .easywave.button import parse_button_info_byte
from .exceptions import InvalidPayloadError
from .sensors import parse_sensor_payload


def _parse_button_byte(info_byte: int) -> tuple[EasywaveButton, ButtonFunction, bool]:
    return parse_button_info_byte(info_byte)


def parse_ewb_rcv(
    info_type: int,
    serial: bytes,
    info_data: bytes,
    *,
    device_type: int | None = None,
) -> EwbRcvEvent:
    """Parse the payload returned by ``ewb_rcv_request``.

    Args:
        info_type: Info type byte from the ICP.
        serial: 16-byte transmitter, sensor, or receiver serial.
        info_data: Additional information field (1 to 8 bytes).
        device_type: Required for ``TM_IT_EWBIDI_STATE`` to decode typed state.
    """
    if info_type == InfoType.TM_IT_EASW_RELEASE:
        return ButtonReleaseEvent(transmitter_serial=serial)

    if info_type == InfoType.TM_IT_EASW_PUSH:
        if not info_data:
            raise InvalidPayloadError("Button push telegram requires at least 1 info byte")
        button, function, should_ignore = _parse_button_byte(info_data[0])
        return ButtonPushEvent(
            transmitter_serial=serial,
            button=button,
            function=function,
            should_ignore=should_ignore,
        )

    if info_type == InfoType.TM_IT_SENSOR_DATA:
        return SensorTelegramEvent(
            sensor_serial=serial,
            payload=parse_sensor_payload(info_data),
        )

    if info_type == InfoType.TM_IT_EWBIDI_STATE:
        if device_type is None:
            raise InvalidPayloadError("device_type is required for EWB state notifications")
        if len(info_data) < 5:
            raise InvalidPayloadError(
                f"EWB state notification requires 5 info bytes, got {len(info_data)}"
            )
        mode = info_data[0]
        state_bytes = info_data[1:5]
        parsed_state = parse_ewb_state(
            device_type,
            mode,
            state_bytes,
            direction=StateDirection.FROM_DEVICE,
        )
        return EwbStateChangeEvent(
            receiver_serial=serial,
            mode=mode,
            state=parsed_state,
        )

    if info_type == InfoType.TM_IT_EWBIDI_ABORT:
        return TransmitterLearnAbortEvent(receiver_serial=serial)

    if info_type == InfoType.TM_IT_EWBIDI_ADD_TR:
        return TransmitterLearnSuccessEvent(receiver_serial=serial)

    if info_type == InfoType.TM_IT_EWBIDI_RMV_TR:
        return TransmitterRemoveSuccessEvent(receiver_serial=serial)

    return UnknownEwbRcvEvent(info_type=info_type, serial=serial, info_data=info_data)


def parse_ewb_rcv_result(
    result: tuple[int, int, bytes, bytes],
    *,
    device_type: int | None = None,
) -> EwbRcvEvent:
    """Parse the tuple returned by ``ewb_rcv_request``."""
    _result_code, info_type, serial, info_data = result
    return parse_ewb_rcv(info_type, serial, info_data, device_type=device_type)


def parse_ew_rcv_ex_result(
    result: tuple[int, int, bytes, bytes],
) -> tuple[int, EwbRcvEvent | None]:
    """Parse the tuple returned by ``ew_rcv_ex_request`` or ``ew_rcv_button_request``."""
    error_code, info_type, serial, info_data = result
    if error_code != 0:
        return error_code, None
    return error_code, parse_ewb_rcv(info_type, serial, info_data)
