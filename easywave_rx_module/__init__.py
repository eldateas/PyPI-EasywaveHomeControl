"""EASYWAVE RX Module Hardware Communication Library.

Pure async implementation for communicating with EASYWAVE radio modules.
Primary API designed for Home Assistant integration.

Async-First Architecture:
    All devices use pure asyncio - no blocking calls on event loop.
    
Device Families:
    RxModule (Binary Protocol):
        - RX11: USB Transceiver (38400 bps)
        - RX21: Serial Module (9600 bps)
        - RX22: Serial Module (9600 bps, enhanced)
        - RX25: Serial Module (38400 bps, high-speed)
    
    RX09 (ASCII Protocol):
        - RX09: Basic Receiver (57600 bps, Easywave Basic only)

Quick Start (Home Assistant):
    >>> from easywave_rx_module import AsyncDeviceFactory
    >>>
    >>> device = await AsyncDeviceFactory.create("RX22", port="/dev/ttyAMA0")
    >>> info = await device.get_device_info()
    >>> success = await device.ping_request()
    >>> functions = await device.get_available_functions()
    >>> await device.disconnect()
"""

from __future__ import annotations

# ============================================================================
# PRIMARY API: Async Factory (Home Assistant)
# ============================================================================

from .async_registry import AsyncDeviceFactory

# ============================================================================
# ASYNC BASE PROTOCOL (Interface)
# ============================================================================

from .protocols.async_base import AsyncBaseProtocol

# ============================================================================
# ASYNC PROTOCOL IMPLEMENTATIONS
# ============================================================================

# RxModule family (binary protocol)
from .protocols.rx11_rx2x import (
    AsyncRX11Device,
    AsyncRX21Device,
    AsyncRX22Device,
    AsyncRX25Device,
    AsyncRxModuleDevice,
    AsyncRxModule,
)

# RX09 family (ASCII protocol)
from .protocols.rx09 import AsyncRX09Device, AsyncRX09Protocol

# ============================================================================
# LEGACY: Sync API (deprecated, for backward compatibility only)
# Will be removed in next major version
# ============================================================================

from .registry import DeviceFactory, DeviceRegistry
from .protocols.base import BaseProtocol
from .protocols.rx11_rx2x import (
    RX11Device,
    RX21Device,
    RX22Device,
    RX25Device,
    RxModuleDevice,
)
from .protocols.rx09 import RX09Device

__version__ = "3.0.0-async"
__all__ = [
    # Primary async API
    "AsyncDeviceFactory",
    "AsyncBaseProtocol",
    "AsyncRxModuleDevice",
    "AsyncRX11Device",
    "AsyncRX21Device",
    "AsyncRX22Device",
    "AsyncRX25Device",
    "AsyncRxModule",
    "AsyncRX09Device",
    "AsyncRX09Protocol",
    # Legacy sync API (deprecated)
    "DeviceFactory",
    "DeviceRegistry",
    "BaseProtocol",
    "RxModuleDevice",
    "RX11Device",
    "RX21Device",
    "RX22Device",
    "RX25Device",
    "RX09Device",
]

__all__ = [
    # Main API: Device Factory (recommended)
    "DeviceFactory",
    "DeviceRegistry",
    # Protocol base class
    "BaseProtocol",
    # Device families
    "RxModule",  # Legacy, for backward compatibility
    "RxModuleDevice",
    "RX11Device",
    "RX21Device",
    "RX22Device",
    "RX25Device",
    "RX09Device",
    # Protocol constants
    "PREFIX",
    "SOP",
    "EOP",
    "STUFFING_MIN",
    "STUFFING_MAX",
    "STUFFING_ADDEND",
    # Function codes
    "FunctionCode",
    "EW_RCV_BUTTON",
    "EW_SEND_CMD",
    "MA_QUERY_HW_VER",
    "MA_QUERY_FW_VER",
    "CANCEL_IO",
    "CANCEL_ALL_IO",
    "PING_RCV",
    # Error codes
    "ErrorCode",
    # Request/response structures
    "IRP",
    "ICP",
    "Request",
    # Helper functions
    "apply_byte_stuffing",
    "remove_byte_stuffing",
    "encode_irp",
    "decode_packet",
    "encode_uint16",
    "encode_uint32",
    "encode_serial_array",
    "parse_icp_data",
    # Constants
    "CONTINUOUS_RCV_FUNCTIONS",
]
