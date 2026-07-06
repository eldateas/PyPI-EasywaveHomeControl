"""EASYWAVE RX Module Hardware Communication Library.

Pure async implementation for communicating with EASYWAVE radio modules.
Primary API designed for Home Assistant integration.

Async-First Architecture:
    All devices use pure asyncio - no blocking calls on event loop.

Device Families:
    RxModule (Binary Protocol):
        - RX11: USB Transceiver (115200 bps)
        - RX21: Serial Module (115200 bps)
        - RX22: Serial Module (115200 bps)
        - RX25: Serial Module (115200 bps)

    RX09 (ASCII Protocol):
        - RX09: Basic Receiver (57600 bps, Easywave Basic only)

Quick Start (Home Assistant):
    >>> from easywave_home_control import AsyncDeviceFactory
    >>>
    >>> device = await AsyncDeviceFactory.create("RX22", port="/dev/ttyAMA0")
    >>> info = await device.get_device_info()
    >>> success = await device.ping_request()
    >>> functions = await device.get_available_functions()
    >>> await device.disconnect()
"""

from __future__ import annotations

from .async_registry import AsyncDeviceFactory

# RX09 family (ASCII protocol, pure async)
from .protocols.rx09 import RX09Device
from .protocols.rx09.protocol import ErrorCode as RX09ErrorCode

# RxModule family (binary protocol, pure async)
from .protocols.rx11_rx2x import (
    RX11Device,
    RX21Device,
    RX22Device,
    RX25Device,
)
from .protocols.rx11_rx2x.protocol import ErrorCode as RX11ErrorCode
from .codec import encode_ewb_state, parse_ewb_rcv, parse_ewb_state
from .codec import secwave

__version__ = "0.2.1"
__all__ = [
    # Factory (primary API)
    "AsyncDeviceFactory",
    # Codec layer
    "encode_ewb_state",
    "parse_ewb_rcv",
    "parse_ewb_state",
    "secwave",
    # Error codes
    "RX11ErrorCode",
    "RX09ErrorCode",
    # RxModule family devices
    "RX11Device",
    "RX21Device",
    "RX22Device",
    "RX25Device",
    # RX09 family devices
    "RX09Device",
]
