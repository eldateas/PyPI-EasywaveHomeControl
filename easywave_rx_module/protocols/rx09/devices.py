"""RX09 device implementations.

RX09 is a simplified Easywave Basic only device with ASCII text protocol.
Pure async implementation using asyncio.
"""

from __future__ import annotations

import logging
from typing import Any

from ...protocols.base import BaseProtocol
from .protocol import RX09Protocol

_LOGGER = logging.getLogger(__name__)


class RX09Device(RX09Protocol, BaseProtocol):
    """EASYWAVE RX09 USB Transceiver (Pure Async).

    RX09 is a simplified Easywave receiver that only supports:
    - Basic Easywave (no Bidi, no Secwave)
    - ASCII text-based commands
    - 57600 baud (fixed)
    - Async API (all methods are async)

    This is the only device in the RX09 family.

    Example:
        ```python
        import asyncio
        from easywave_rx_module.protocols.rx09.devices import RX09Device

        async def main():
            device = RX09Device('/dev/ttyUSB0')
            await device.connect()
            try:
                result, vendor_id, device_id, version = await device.get_device_id()
                if result == 0:
                    print(f"Device: {device_id:02X} Vendor: {vendor_id:02X} Version: {version:02X}")
            finally:
                await device.disconnect()

        asyncio.run(main())
        ```
    """

    DEVICE_TYPE = "RX09"
    DEFAULT_BAUDRATE = 57600
    DEFAULT_VARIANT = "basic"

    def __init__(
        self,
        port: str,
        timeout: float = 5.0,
        variant: str | None = None,
    ) -> None:
        """Initialize RX09 device.

        Args:
            port: Serial port path (e.g., '/dev/ttyUSB0', 'COM3')
            timeout: Read timeout in seconds
            variant: Protocol variant (reserved for future use, must be 'basic')
        """
        # Initialize through RX09Protocol (which inherits BaseProtocol)
        RX09Protocol.__init__(
            self,
            port=port,
            timeout=timeout,
            variant=variant or self.DEFAULT_VARIANT,
        )

    async def get_device_info(self) -> dict[str, Any]:
        """Get device information including variant.

        Returns:
            Dictionary with device metadata
        """
        return {
            "device_type": self.DEVICE_TYPE,
            "port": self.port,
            "baudrate": self.BAUDRATE,
            "variant": self.variant,
            "connection_type": "USB Serial",
            "protocol": "ASCII Text-based (Easywave Basic only)",
            "implementation": "Pure Async (asyncio)",
        }

    async def get_available_functions(self) -> dict[str, str]:
        """Get available API functions.

        Returns:
            Dictionary of function names and descriptions
        """
        # RX09 only supports basic Easywave (no variants, no filtering needed)
        return await super().get_available_functions()
