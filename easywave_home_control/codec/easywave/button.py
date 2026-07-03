"""Easywave Basic button/function byte (Spec EW_SEND_CMD / EW_RCV_EX offset 20)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from ..events import ButtonFunction, EasywaveButton


class EasywaveSendButton(IntEnum):
    A = 0
    B = 1
    C = 2
    D = 3


def encode_send_button_byte(
    button: EasywaveSendButton | EasywaveButton | int,
    *,
    function: ButtonFunction | int = ButtonFunction.DEFAULT,
) -> int:
    """Encode the EW_SEND_CMD button byte (Spec page 89)."""
    button_value = int(button)
    function_value = int(function)
    if not 0 <= button_value <= 3:
        raise ValueError(f"button must be 0-3, got {button_value}")
    if function_value == int(ButtonFunction.LOW_BATTERY):
        return 0x80
    return (button_value & 0x03) | ((function_value << 2) & 0xFC)


def parse_button_info_byte(info_byte: int) -> tuple[EasywaveButton, ButtonFunction, bool]:
    """Decode the first info byte of EW_RCV_EX / EW_RCV_BUTTON / EWB_RCV."""
    if info_byte == 0x80:
        return EasywaveButton.A, ButtonFunction.LOW_BATTERY, False

    button_map = {
        0: EasywaveButton.A,
        1: EasywaveButton.B,
        2: EasywaveButton.C,
        3: EasywaveButton.D,
    }
    function_map = {
        0: ButtonFunction.DEFAULT,
        1: ButtonFunction.REMOTE_LEARN_DELETE,
        2: ButtonFunction.REMOTE_LEARN_ADD,
        3: ButtonFunction.REMOTE_LEARN_RESET,
        4: ButtonFunction.REMOTE_LEARN_TIMER,
        5: ButtonFunction.EMULATED_HOLD,
        6: ButtonFunction.EMULATED_RELEASE,
    }

    button = button_map.get(info_byte & 0x03, EasywaveButton(info_byte & 0x03))
    function_raw = (info_byte & 0xFC) >> 2
    function = function_map.get(function_raw, ButtonFunction(function_raw))
    should_ignore = function in (
        ButtonFunction.REMOTE_LEARN_DELETE,
        ButtonFunction.REMOTE_LEARN_ADD,
        ButtonFunction.REMOTE_LEARN_RESET,
        ButtonFunction.REMOTE_LEARN_TIMER,
    )
    return button, function, should_ignore
