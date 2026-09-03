"""USB serial discovery helpers.

Blocking enumeration / port probes must never run on the asyncio event loop.
Callers should either:

* ``await async_find_usb_device(...)`` (preferred), or
* ``await loop.run_in_executor(None, find_usb_device, ...)`` for the sync API.
"""

from __future__ import annotations

import asyncio
import logging

from ..serial_io import (
    SERIAL_ERRORS,
    async_list_serial_ports,
    list_serial_ports,
    serial_for_url,
)

_LOGGER = logging.getLogger(__name__)

SERIAL_OR_OS_ERRORS: tuple[type[Exception], ...] = SERIAL_ERRORS

__all__ = [
    "SERIAL_OR_OS_ERRORS",
    "async_find_usb_device",
    "async_lookup_port_serial",
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

    Blocking — run via ``run_in_executor`` or prefer ``async_find_usb_device``.

    Returns:
        ``(device_path, usb_serial_number)`` or ``None``.
    """
    try:
        ports = list(list_serial_ports())
    except SERIAL_OR_OS_ERRORS:
        _LOGGER.exception("Error while enumerating serial ports")
        return None

    for port in ports:
        if (port.vid, port.pid) not in usb_ids:
            continue
        if test_serial_port(port.device, baudrate=baudrate):
            return port.device, port.serial_number or "unknown"
    return None


async def async_find_usb_device(
    usb_ids: frozenset[tuple[int, int]],
    *,
    baudrate: int = 115200,
) -> tuple[str, str] | None:
    """Async USB discovery using ``serialx.async_list_serial_ports``."""
    try:
        ports = await async_list_serial_ports()
    except SERIAL_OR_OS_ERRORS:
        _LOGGER.exception("Error while enumerating serial ports")
        return None

    for port in ports:
        if (port.vid, port.pid) not in usb_ids:
            continue
        # Brief open/close probe stays sync and cheap; offload to executor.
        ok = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda p=port.device: test_serial_port(p, baudrate=baudrate),
        )
        if ok:
            return port.device, port.serial_number or "unknown"
    return None


def lookup_port_serial(device_path: str) -> str | None:
    """Return the USB serial number for ``device_path``, if present."""
    try:
        for port in list_serial_ports():
            if port.device == device_path:
                return port.serial_number
    except SERIAL_OR_OS_ERRORS as err:
        _LOGGER.debug("Could not look up USB serial for %s: %s", device_path, err)
    return None


async def async_lookup_port_serial(device_path: str) -> str | None:
    """Async variant of :func:`lookup_port_serial`."""
    try:
        for port in await async_list_serial_ports():
            if port.device == device_path:
                return port.serial_number
    except SERIAL_OR_OS_ERRORS as err:
        _LOGGER.debug("Could not look up USB serial for %s: %s", device_path, err)
    return None


def test_serial_port(port_path: str, *, baudrate: int = 115200) -> bool:
    """Return whether ``port_path`` can be opened briefly (blocking)."""
    try:
        test_port = serial_for_url(port_path, baudrate=baudrate, read_timeout=0.5)
        test_port.close()
    except SERIAL_ERRORS:
        return False
    return True
