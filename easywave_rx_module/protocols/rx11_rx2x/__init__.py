"""RxModule protocol family (Pure Async).

Provides async implementations for RxModule protocol devices.

Device Types:
    RX11: USB Transceiver (115200 bps)
    RX21: Serial Module (115200 bps)
    RX22: Serial Module (115200 bps)
    RX25: Serial Module (115200 bps)
"""

# Pure async devices
from .devices import RX11Device, RX21Device, RX22Device, RX25Device, RxModuleDevice
from .protocol import (
    CANCEL_ALL_IO,
    CANCEL_IO,
    CONTINUOUS_RCV_FUNCTIONS,
    EOP,
    EW_RCV_BUTTON,
    EW_SEND_CMD,
    ICP,
    IRP,
    PREFIX,
    SOP,
    STUFFING_ADDEND,
    STUFFING_MAX,
    STUFFING_MIN,
    ErrorCode,
    FunctionCode,
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
