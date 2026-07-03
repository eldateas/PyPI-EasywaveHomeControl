"""Pure RX09 response parsing (Spec SP_RTR09_DE_0809)."""

from __future__ import annotations


def parse_status_response(response: str) -> bool | None:
    """Parse generic OK/ERROR status."""
    if response == "OK":
        return True
    if response == "ERROR":
        return False
    return None


def parse_id_response(response: str) -> tuple[int, int, int] | None:
    """Parse ``ID,<vendor>,<device>,<version>``."""
    parts = response.split(",")
    if len(parts) < 4 or parts[0] != "ID":
        return None
    try:
        return int(parts[1], 16), int(parts[2], 16), int(parts[3], 16)
    except ValueError:
        return None


def parse_getp_response(response: str) -> int | None:
    """Parse ``GETP,<count>``."""
    parts = response.split(",")
    if len(parts) < 2 or parts[0] != "GETP":
        return None
    try:
        return int(parts[1], 16)
    except ValueError:
        return None


def parse_rdp_response(response: str, *, expected_position: int | None = None) -> int | None:
    """Parse ``RDP,<position>,<serial>`` (22-bit serial in 4 hex bytes)."""
    parts = response.split(",")
    if len(parts) < 3 or parts[0] != "RDP":
        return None
    try:
        position = int(parts[1], 16)
        serial = int(parts[2], 16)
    except ValueError:
        return None
    if expected_position is not None and position != expected_position:
        return None
    return serial


def parse_rec_message(message: str) -> tuple[int, str] | None:
    """Parse spontaneous ``REC,<serial>,<button>``."""
    parts = message.split(",")
    if len(parts) < 3 or parts[0] != "REC":
        return None
    button = parts[2].strip().upper()
    if button not in ("A", "B", "C", "D"):
        return None
    try:
        serial = int(parts[1], 16)
    except ValueError:
        return None
    return serial, button


def parse_echo_response(response: str) -> bool | None:
    if response == "Echo is ON":
        return True
    if response == "Echo is OFF":
        return False
    return None


def parse_led_response(response: str) -> bool | None:
    if response == "Led is ON":
        return True
    if response == "Led is OFF":
        return False
    return None


def parse_button_response(response: str) -> bool | None:
    if response == "Button is pressed":
        return True
    if response == "Button is released":
        return False
    return None


def parse_bootloader_response(response: str) -> bool:
    return response == "Bootloader is starting now !"
