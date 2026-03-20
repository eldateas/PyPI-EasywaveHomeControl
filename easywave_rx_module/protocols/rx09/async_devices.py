"""Async RX09 device implementation.

Pure asyncio device for RX09 ASCII Basic Receiver.
"""

from __future__ import annotations

from typing import Any

from ...protocols.async_base import AsyncBaseProtocol
from .async_protocol import AsyncRX09Protocol


class AsyncRX09Device(AsyncBaseProtocol):
    """Async device for RX09 ASCII protocol.

    Pure asyncio implementation for RX09 Easywave Basic Receiver.
    """

    DEVICE_TYPE = "RX09"
    BAUDRATE = 57600  # Fixed baudrate for RX09

    def __init__(
        self,
        port: str,
        baudrate: int | None = None,
        timeout: float = 5.0,
        variant: str | None = None,
    ) -> None:
        """Initialize async RX09 device.

        Args:
            port: Serial port path
            baudrate: Ignored (RX09 fixed at 57600)
            timeout: Default timeout for operations
            variant: Device variant (usually 'basic')
        """
        self.port = port
        self.baudrate = self.BAUDRATE  # Always 57600
        self.timeout = timeout
        self.variant = variant or "basic"

        # Create protocol instance
        self._protocol = AsyncRX09Protocol(port=port)

    async def connect(self) -> bool:
        """Connect to device."""
        return await self._protocol.connect()

    async def disconnect(self) -> None:
        """Disconnect from device."""
        await self._protocol.disconnect()

    async def ping_request(self, timeout: float = 5.0) -> bool:
        """Ping device.

        Args:
            timeout: Timeout in seconds

        Returns:
            True if device responded
        """
        result = await self._protocol.ping(timeout)
        return result == 0

    async def get_device_info(self) -> dict[str, Any]:
        """Get device information."""
        return {
            "device_type": self.DEVICE_TYPE,
            "port": self.port,
            "baudrate": self.BAUDRATE,
            "variant": self.variant,
            "protocol": "ASCII Text (RX09)",
            "functions": 11,
        }

    async def get_available_functions(self) -> dict[str, str]:
        """Get available functions (11 for RX09)."""
        return {
            # System
            "ping": "Ping device",
            "get_device_id": "Get device ID and version",
            "query_positions": "Query number of positions",
            # Position management
            "read_position_data": "Read position serial number",
            # Transmission
            "send_telegramm": "Send telegramm",
            "receive_telegramm": "Wait for telegramm reception",
            # Status & control
            "query_echo": "Query echo setting",
            "set_echo": "Set echo mode",
            "query_led": "Query LED status",
            "set_led": "Control LED",
            "query_button": "Query button status",
        }

    # ========================================================================
    # RX09-SPECIFIC ASYNC METHODS
    # ========================================================================

    async def get_device_id(self) -> tuple[int, dict]:
        """Get device ID."""
        return await self._protocol.get_device_id()

    async def query_positions(self) -> tuple[int, int]:
        """Query positions."""
        return await self._protocol.query_positions()

    async def read_position_data(self, position: int) -> tuple[int, int]:
        """Read position data."""
        return await self._protocol.read_position_data(position)

    async def send_telegramm(self, position: int, button: str) -> tuple[int, str]:
        """Send telegramm."""
        return await self._protocol.send_telegramm(position, button)

    async def receive_telegramm(self, timeout: float = 5.0) -> tuple[int, dict]:
        """Receive telegramm."""
        return await self._protocol.receive_telegramm(timeout)

    async def query_echo(self) -> tuple[int, bool]:
        """Query echo."""
        return await self._protocol.query_echo()

    async def set_echo(self, enabled: bool) -> tuple[int, str]:
        """Set echo."""
        return await self._protocol.set_echo(enabled)

    async def query_led(self) -> tuple[int, bool]:
        """Query LED."""
        return await self._protocol.query_led()

    async def set_led(self, enabled: bool) -> tuple[int, str]:
        """Set LED."""
        return await self._protocol.set_led(enabled)

    async def query_button(self) -> tuple[int, str]:
        """Query button."""
        return await self._protocol.query_button()
