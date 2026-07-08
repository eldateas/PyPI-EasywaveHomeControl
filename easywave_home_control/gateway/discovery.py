"""USB serial discovery helpers (blocking — run in an executor)."""

from __future__ import annotations

import logging

import serial
import serial.tools.list_ports

_LOGGER = logging.getLogger(__name__)

_SERIAL_ERRORS: tuple[type[Exception], ...] = (
    serial.SerialException,
    serial.SerialTimeoutException,
)
SERIAL_OR_OS_ERRORS: tuple[type[Exception], ...] = (
    *_SERIAL_ERRORS,
    OSError,
)

__all__ = [
    "SERIAL_OR_OS_ERRORS",
    "find_usb_device",
    "lookup_port_serial",
    "test_serial_port",
]


def find_usb_device(
    usb_ids: frozenset[tuple[int, int]],
    *,
    baudrate: int = 115200,
) -> tuple[str, str] | None:
    """Find the first openable serial port matching ``usb_ids``.

    Returns:
        ``(device_path, usb_serial_number)`` or ``None``.
    """
    try:
        ports = list(serial.tools.list_ports.comports())
    except SERIAL_OR_OS_ERRORS:
        _LOGGER.exception("Error while enumerating serial ports")
        return None

    for port in ports:
        if (port.vid, port.pid) not in usb_ids:
            continue
        if test_serial_port(port.device, baudrate=baudrate):
            return port.device, port.serial_number or "unknown"
    return None


def lookup_port_serial(device_path: str) -> str | None:
    """Return the USB serial number for ``device_path``, if present."""
    try:
        for port in serial.tools.list_ports.comports():
            if port.device == device_path:
                return port.serial_number
    except _SERIAL_OR_OS_ERRORS as err:
        _LOGGER.debug("Could not look up USB serial for %s: %s", device_path, err)
    return None


def test_serial_port(port_path: str, *, baudrate: int = 115200) -> bool:
    """Return whether ``port_path`` can be opened briefly."""
    try:
        test_port = serial.Serial(port=port_path, baudrate=baudrate, timeout=0.5)
        test_port.close()
    except _SERIAL_ERRORS:
        return False
    return True
