"""RxModule protocol family (Pure Async).

Provides async implementations for RxModule protocol devices.

Device Types:
    RX11: USB Transceiver (115200 bps)
    RX21: Serial Module (115200 bps)
    RX22: Serial Module (115200 bps)
    RX25: Serial Module (115200 bps)
"""

from .devices import RX11Device, RX21Device, RX22Device, RX25Device
from .protocol import ErrorCode

__all__ = [
    "RX11Device",
    "RX21Device",
    "RX22Device",
    "RX25Device",
    "ErrorCode",
]
