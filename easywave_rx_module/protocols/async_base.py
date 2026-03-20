"""Async base protocol interface for all device families.

Defines the abstract interface that all async device implementations must follow.
This is the primary API for Home Assistant integration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AsyncBaseProtocol(ABC):
    """Abstract base class for async protocol implementations.

    All async device classes must inherit from this and implement these methods.
    This ensures consistent async/await interface across all device families.
    """

    @abstractmethod
    async def ping_request(self, timeout: float = 5.0) -> bool:
        """Ping device to verify connection (required by all devices).

        Args:
            timeout: Timeout in seconds

        Returns:
            True if device responded, False on timeout/error
        """
        ...

    @abstractmethod
    async def get_device_info(self) -> dict[str, Any]:
        """Get device information (type, port, baudrate, etc).

        Returns:
            Dictionary with device metadata
        """
        ...

    @abstractmethod
    async def get_available_functions(self) -> dict[str, str]:
        """Get list of available functions for this device.

        Returns:
            Dictionary of function names and descriptions
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from device gracefully.

        Called during HA shutdown or error recovery.
        """
        ...
