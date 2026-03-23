"""Protocol implementations for EASYWAVE devices.

This package contains protocol implementations for different device families:

1. RxModule Family (rxmodule/):
   - RX11: USB Transceiver (115200 bps)
   - RX21: Serial Module (115200 bps)
   - RX22: Serial Module (115200 bps)
   - RX25: Serial Module (115200 bps)
   - Variants: ew, dev, basic, pro

2. RX09 Family (rx09/):
   - RX09: Different protocol, different functions
   - (Template for future families)

Each family implements a BaseProtocol interface and may offer variants
with different functional subsets.
"""

from .base import BaseProtocol

__all__ = ["BaseProtocol"]
