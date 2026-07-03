"""Codec-layer exceptions."""

from __future__ import annotations


class CodecError(Exception):
    """Base class for codec errors."""


class UnknownModeError(CodecError):
    """Raised when mode is not supported for a device type and direction."""

    def __init__(self, mode: int, device_type: int, *, direction: str | None = None) -> None:
        self.mode = mode
        self.device_type = device_type
        self.direction = direction
        detail = f"mode={mode}, device_type=0x{device_type:02x}"
        if direction:
            detail += f", direction={direction}"
        super().__init__(f"Unsupported EWB state mode: {detail}")


class InvalidPayloadError(CodecError):
    """Raised when telegram or sensor payload has invalid length or content."""
