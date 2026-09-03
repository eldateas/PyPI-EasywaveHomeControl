"""Event-loop-safe serial helpers built on ``serialx``.

Home Assistant's ``async-dependency`` quality rule requires that libraries
never perform blocking serial I/O on the asyncio event loop.  This module
centralises the serialx imports and exception types used throughout the
library:

* **Async path (RxModule):** ``async_serial_for_url`` / ``AsyncSerial`` —
  open, read, write, and close are all ``await``-able and never block the
  loop.
* **Sync path (USB discovery):** ``serial_for_url`` / ``list_serial_ports``
  may only be called from a worker thread (``run_in_executor``) or from
  ``async_list_serial_ports``.

Internals ownership
-------------------
* asyncio tasks own protocol framing, request queues, and gateway lifecycle.
* serialx owns the OS file descriptor and schedules reads via the loop's
  reader callback — there is no busy-wait ``in_waiting`` polling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import serialx
from serialx import (
    SerialException,
    async_list_serial_ports,
    async_serial_for_url,
    list_serial_ports,
    serial_for_url,
)

if TYPE_CHECKING:
    from serialx.async_serial import AsyncSerial
    from serialx.common import BaseSerial, SerialPortInfo

# serialx raises native OSError / TimeoutError for I/O failures; SerialException
# covers protocol/backend failures.  Catch the union everywhere we touch serial.
SERIAL_ERRORS: tuple[type[Exception], ...] = (SerialException, OSError, TimeoutError)

__all__ = [
    "SERIAL_ERRORS",
    "AsyncSerial",
    "BaseSerial",
    "SerialException",
    "SerialPortInfo",
    "async_list_serial_ports",
    "async_serial_for_url",
    "list_serial_ports",
    "serial_for_url",
    "serialx",
]
