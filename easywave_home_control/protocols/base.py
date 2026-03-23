"""Base protocol interface for all EASYWAVE device families.

Defines the abstract interface that all device implementations must follow.
Pure async implementation using asyncio.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeVar

T = TypeVar("T", bound="BaseProtocol")


class BaseProtocol(ABC):
    """Abstract base class for EASYWAVE protocol implementations.

    All device classes must inherit from this and implement these methods.
    This ensures consistent async/await interface across all device families.
    """

    @classmethod
    async def create(cls: type[T], port: str, **kwargs: Any) -> T:
        """Create and connect device instance.

        This factory method instantiates the device and connects it in one step.

        Args:
            port: Serial port path (e.g., "/dev/ttyUSB0")
            **kwargs: Additional keyword arguments for device initialization
                (timeout, variant, etc.)

        Returns:
            Connected device instance

        Example:
            >>> device = await RX11Device.create(port="/dev/ttyUSB0")
            >>> # Device is already connected and ready to use
            >>> info = await device.get_device_info()
            >>> await device.disconnect()

        Raises:
            Exception: If connection fails or device is not found
        """
        device = cls(port, **kwargs)  # type: ignore[operator]
        await device.connect()
        return device

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to device asynchronously.

        This method must be called before using any device operations.

        Returns:
            True if connection successful, False on failure
        """
        ...

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
