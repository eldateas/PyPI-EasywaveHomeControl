"""EASYWAVE RX Module Hardware Communication Library.

Pure Python implementation for communicating with EASYWAVE radio modules
including RX11 USB transceivers and RX21/RX22/RX25 direct serial modules.

With support for multiple protocol families (RxModule, RX09, etc.) and
functional variants (ew, dev, basic, pro).

Device Families & Types:
    RxModule Family:
        - RX11: USB-based transceiver (38400 bps)
        - RX21: Direct serial module (9600 bps)
        - RX22: Direct serial module (9600 bps, enhanced)
        - RX25: Direct serial module (38400 bps, high-speed)
    
    RX09 Family:  (Template for future devices with different protocols)
        - RX09: Different protocol, different functions

Functional Variants (for RxModule family):
    - basic: Essential functions only
    - ew: EasyWave consumer functions
    - dev: All available functions

Quick Start:
    >>> from easywave_rx_module import DeviceFactory
    >>>
    >>> # Create device with variant
    >>> rx11 = DeviceFactory.create("RX11-EW", port="/dev/ttyUSB0")
    >>>
    >>> # Check available functions
    >>> available = rx11.get_available_functions()
    >>>
    >>> # Use protocol
    >>> rx11.ping_request()
    >>> device_info = rx11.query_hw_version_request()

Architecture:
    BaseProtocol (interface)
        ├── RxModule Family (protocols/rx11_rx2x/)
        │   ├── RX11Device (USB, 38400 bps)
        │   ├── RX21Device (Serial, 9600 bps)
        │   ├── RX22Device (Serial, 9600 bps enhanced)
        │   └── RX25Device (Serial, 38400 bps)
        │
        └── RX09 Family (protocols/rx09/) [TEMPLATE]
            └── RX09Device (Different protocol)

Device creation is via DeviceFactory using string identifiers.
Each device can operate in different variants controlling available API.
"""

from __future__ import annotations

# Main API: DeviceFactory for creating devices
from .registry import DeviceFactory, DeviceRegistry

# Protocol families (new structure)
from .protocols.base import BaseProtocol
from .protocols.rx11_rx2x import (
    RX11Device,
    RX21Device,
    RX22Device,
    RX25Device,
    RxModuleDevice,
)
from .protocols.rx09 import RX09Device

# Protocol constants and utilities from protocols
from .protocols.rx11_rx2x.protocol import (
    CANCEL_ALL_IO,
    CANCEL_IO,
    CONTINUOUS_RCV_FUNCTIONS,
    EOP,
    EW_RCV_BUTTON,
    EW_SEND_CMD,
    MA_QUERY_FW_VER,
    MA_QUERY_HW_VER,
    PING_RCV,
    PREFIX,
    SOP,
    STUFFING_ADDEND,
    STUFFING_MAX,
    STUFFING_MIN,
    ErrorCode,
    FunctionCode,
    ICP,
    IRP,
    Request,
    RxModule,
    apply_byte_stuffing,
    decode_packet,
    encode_irp,
    encode_serial_array,
    encode_uint16,
    encode_uint32,
    parse_icp_data,
    remove_byte_stuffing,
)

__version__ = "2.0.0"

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
