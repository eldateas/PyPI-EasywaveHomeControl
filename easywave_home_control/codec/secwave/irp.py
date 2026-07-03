"""Secwave IRP parameter encoding (Spec section Secwave)."""

from __future__ import annotations

import struct

from ..exceptions import InvalidPayloadError
from .models import SecSendCmdTelRequest
from .states import SecwaveReplyState, encode_reply_state

MAX_STORAGE_INDEX = 127


def validate_storage_index(storage_index: int) -> None:
    if not 0 <= storage_index <= MAX_STORAGE_INDEX:
        raise InvalidPayloadError(
            f"storage_index must be 0-{MAX_STORAGE_INDEX}, got {storage_index}"
        )


def validate_button_number(button_number: int) -> None:
    if not 0 <= button_number <= MAX_STORAGE_INDEX:
        raise InvalidPayloadError(
            f"button_number must be 0-{MAX_STORAGE_INDEX}, got {button_number}"
        )


def encode_sec_learn_params(user_data: int) -> bytes:
    """SEC_LEARN IRP params: 4-byte user data (Spec offset 1-4)."""
    return struct.pack(">I", user_data & 0xFFFFFFFF)


def encode_sec_storage_index_params(storage_index: int) -> bytes:
    """SEC_STAT / SEC_DELETE IRP params (Spec offset 1-2)."""
    validate_storage_index(storage_index)
    return struct.pack(">H", storage_index)


def encode_sec_wr_userdata_params(storage_index: int, user_data: int) -> bytes:
    """SEC_WR_USERDATA IRP params (Spec offset 1-6)."""
    return encode_sec_storage_index_params(storage_index) + struct.pack(
        ">I", user_data & 0xFFFFFFFF
    )


def encode_sec_send_cmd_tel_params(request: SecSendCmdTelRequest) -> bytes:
    """SEC_SEND_CMD_TEL / SEC_SEND_LRN_TEL IRP params (Spec offset 1-6)."""
    validate_button_number(request.button_number)
    return struct.pack(
        ">HBHB",
        request.button_number,
        request.query.to_byte(),
        request.command & 0xFFFF,
        request.flags.to_byte(),
    )


def encode_sec_reply_query_params(reply: SecwaveReplyState) -> bytes:
    """SEC_REPLY_QUERY IRP params: primary + secondary state (Spec offset 1-4)."""
    primary, secondary = encode_reply_state(reply)
    return struct.pack(">HH", primary, secondary)
