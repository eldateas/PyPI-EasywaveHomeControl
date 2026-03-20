"""RX09 device implementations.

RX09 is a simplified Easywave Basic only device with ASCII text protocol.
"""

from typing import Any

from ...protocols.base import BaseProtocol
from .protocol import RX09Protocol


class RX09Device(RX09Protocol, BaseProtocol):
    """EASYWAVE RX09 USB Transceiver.

    RX09 is a simplified Easywave receiver that only supports:
    - Basic Easywave (no Bidi, no Secwave)
    - ASCII text-based commands
    - 57600 baud

    This is the only device in the RX09 family.
    """

    DEVICE_TYPE = "RX09"
    DEFAULT_BAUDRATE = 57600
    DEFAULT_VARIANT = "basic"

    def __init__(
        self,
        port: str,
        baudrate: int | None = None,
        timeout: float = 5.0,
        variant: str | None = None,
    ) -> None:
        """Initialize RX09 device.

        Args:
            port: Serial port path
            baudrate: Communication baudrate (defaults to 57600)
            timeout: Read timeout in seconds
            variant: Protocol variant (reserved for future use)
        """
        # Initialize through RX09Protocol
        RX09Protocol.__init__(
            self,
            port=port,
            baudrate=baudrate or self.DEFAULT_BAUDRATE,
            timeout=timeout,
            variant=variant or self.DEFAULT_VARIANT,
        )

    def get_device_info(self) -> dict[str, Any]:
        """Get device information including variant.

        Returns:
            Dictionary with device metadata
        """
        return {
            "device_type": self.DEVICE_TYPE,
            "port": self.port,
            "baudrate": self.baudrate,
            "variant": self.variant,
            "connection_type": "USB Serial",
            "protocol": "ASCII Text-based (Easywave Basic only)",
        }

    def get_available_functions(self) -> dict[str, str]:
        """Get available API functions.

        Returns:
            Dictionary of function names and descriptions
        """
        # RX09 only supports basic Easywave (no variants, no filtering needed)
        return super().get_available_functions()
