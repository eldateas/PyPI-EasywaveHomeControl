"""Async device implementations for all EASYWAVE device families.

Pure async devices using AsyncRxModule and AsyncRX09Protocol.
These are the primary classes used by Home Assistant.
"""

from __future__ import annotations

from typing import Any

from ...protocols.async_base import AsyncBaseProtocol
from .async_protocol import AsyncRxModule


class AsyncRxModuleDevice(AsyncBaseProtocol):
    """Async device for RxModule family (RX11, RX21, RX22, RX25).

    Pure asyncio implementation - no blocking calls.
    """

    DEVICE_TYPE: str = "RX_BASE"
    DEFAULT_BAUDRATE: int = 38400

    def __init__(
        self,
        port: str,
        baudrate: int | None = None,
        timeout: float = 5.0,
        variant: str | None = None,
    ) -> None:
        """Initialize async RxModule device.

        Args:
            port: Serial port path
            baudrate: Baudrate (uses device default if None)
            timeout: Default timeout for operations
            variant: Device variant (ew, dev, basic, etc.)
        """
        self.port = port
        self.baudrate = baudrate or self.DEFAULT_BAUDRATE
        self.timeout = timeout
        self.variant = variant or "ew"

        # Create protocol instance
        self._protocol = AsyncRxModule(port=port, baudrate=self.baudrate)

    async def connect(self) -> bool:
        """Connect to device."""
        return await self._protocol.connect()

    async def disconnect(self) -> None:
        """Disconnect from device."""
        await self._protocol.disconnect()

    async def ping_request(self, timeout: float = 5.0) -> bool:
        """Ping device (required by AsyncBaseProtocol).

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
            "baudrate": self.baudrate,
            "variant": self.variant,
            "connection_type": "USB Serial" if "USB" in self.DEVICE_TYPE else "Direct Serial",
        }

    async def get_available_functions(self) -> dict[str, str]:
        """Get available functions for this device."""
        return {
            # System
            "ping": "Ping device",
            "query_hw_version": "Query hardware version",
            "query_fw_version": "Query firmware version",
            # EW
            "ew_get_fd_serial_request": "Get EW serial number",
            "ew_rcv_button_request": "Receive EW button",
            "ew_send_cmd_request": "Send EW command",
            "ew_rcv_ex_request": "Receive extended telegram",
            # EWB
            "ewb_get_fd_serial_request": "Get EWB serial",
            "ewb_rcv_request": "Receive EWB telegram",
            "ewb_change_state_request": "Change EWB state",
            "ewb_query_state_request": "Query EWB state",
            # SEC
            "sec_rcv_request": "Receive security telegram",
            "sec_learn_request": "Learn security device",
        }

    # ========================================================================
    # DIRECT METHOD DELEGATIONS (async)
    # ========================================================================

    async def query_hw_version(self) -> tuple[int, str]:
        """Query hardware version."""
        return await self._protocol.query_hw_version()

    async def query_fw_version(self) -> tuple[int, str]:
        """Query firmware version."""
        return await self._protocol.query_fw_version()

    async def ew_send_cmd_request(
        self, gateway_id: int, button: int
    ) -> tuple[int, bytes]:
        """Send EW command."""
        return await self._protocol.ew_send_cmd_request(gateway_id, button)

    async def ew_rcv_button_request(self) -> tuple[int, bytes]:
        """Receive EW button press."""
        return await self._protocol.ew_rcv_button_request()


# Specific device implementations (just inherit with different defaults)


class AsyncRX11Device(AsyncRxModuleDevice):
    """EASYWAVE RX11 USB Transceiver."""

    DEVICE_TYPE = "RX11"
    DEFAULT_BAUDRATE = 115200


class AsyncRX21Device(AsyncRxModuleDevice):
    """EASYWAVE RX21 Serial Module (115200 bps)."""

    DEVICE_TYPE = "RX21"
    DEFAULT_BAUDRATE = 115200


class AsyncRX22Device(AsyncRxModuleDevice):
    """EASYWAVE RX22 Serial Module (115200 bps enhanced)."""

    DEVICE_TYPE = "RX22"
    DEFAULT_BAUDRATE = 115200


class AsyncRX25Device(AsyncRxModuleDevice):
    """EASYWAVE RX25 Serial Module (115200 bps high-speed)."""

    DEVICE_TYPE = "RX25"
    DEFAULT_BAUDRATE = 115200
