"""RxModule protocol family.

Provides implementations for RxModule protocol devices.

Device Types:
    RX11: USB Transceiver (38400 bps)
    RX21: Serial Module (9600 bps)
    RX22: Serial Module (9600 bps, enhanced)
    RX25: Serial Module (38400 bps, high-speed)
"""

# Sync devices (legacy, will be removed)
from .devices import RX11Device, RX21Device, RX22Device, RX25Device, RxModuleDevice

# Async devices (primary API for Home Assistant)
from .async_devices import (
    AsyncRX11Device,
    AsyncRX21Device,
    AsyncRX22Device,
    AsyncRX25Device,
    AsyncRxModuleDevice,
)
from .async_protocol import AsyncRxModule

from .protocol import (
    CANCEL_ALL_IO,
    CANCEL_IO,
    CONTINUOUS_RCV_FUNCTIONS,
    EOP,
    EW_RCV_BUTTON,
    EW_SEND_CMD,
    ErrorCode,
    FunctionCode,
    ICP,
    IRP,
    PREFIX,
    Request,
    RxModule,
    SOP,
    STUFFING_ADDEND,
    STUFFING_MAX,
    STUFFING_MIN,
    apply_byte_stuffing,
    decode_packet,
    encode_irp,
    encode_serial_array,
    encode_uint16,
    encode_uint32,
    parse_icp_data,
    remove_byte_stuffing,
)

__all__ = [
    "RxModule",
    "RxModuleDevice",
    "RX11Device",
    "RX21Device",
    "RX22Device",
    "RX25Device",
    # Protocol exports
    "PREFIX",
    "SOP",
    "EOP",
    "STUFFING_MIN",
    "STUFFING_MAX",
    "STUFFING_ADDEND",
    "FunctionCode",
    "ErrorCode",
    "IRP",
    "ICP",
    "Request",
    "apply_byte_stuffing",
    "remove_byte_stuffing",
    "encode_irp",
    "decode_packet",
    "encode_uint16",
    "encode_uint32",
    "encode_serial_array",
    "parse_icp_data",
    "EW_RCV_BUTTON",
    "EW_SEND_CMD",
    "CANCEL_IO",
    "CANCEL_ALL_IO",
    "CONTINUOUS_RCV_FUNCTIONS",
]
