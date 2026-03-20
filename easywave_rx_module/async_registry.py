"""Async device factory for Home Assistant integration.

Simplified factory that creates pure async devices.
No ThreadPoolExecutor wrapper - direct asyncio implementation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Literal

from .protocols.async_base import AsyncBaseProtocol
from .protocols.rx09 import AsyncRX09Device
from .protocols.rx11_rx2x import (
    AsyncRX11Device,
    AsyncRX21Device,
    AsyncRX22Device,
    AsyncRX25Device,
)

_LOGGER = logging.getLogger(__name__)

# Device type aliases
ASYNC_DEVICE_ID = Literal[
    "RX11",
    "RX11-BASIC",
    "RX11-EW",
    "RX11-DEV",
    "RX21",
    "RX21-BASIC",
    "RX21-EW",
    "RX21-DEV",
    "RX22",
    "RX22-BASIC",
    "RX22-EW",
    "RX22-DEV",
    "RX25",
    "RX25-BASIC",
    "RX25-EW",
    "RX25-DEV",
    "RX09",
    "RX09-BASIC",
]

# Device registry
_DEVICE_REGISTRY: dict[str, type[AsyncBaseProtocol]] = {
    # RX11
    "RX11": AsyncRX11Device,
    # RX21
    "RX21": AsyncRX21Device,
    # RX22
    "RX22": AsyncRX22Device,
    # RX25
    "RX25": AsyncRX25Device,
    # RX09
    "RX09": AsyncRX09Device,
}


class AsyncDeviceFactory:
    """Factory for creating pure async EASYWAVE devices.

    Direct asyncio implementation - no thread pool wrapper.
    Primary API for Home Assistant integration.

    Example (HA integration):
        ```python
        from easywave_rx_module import AsyncDeviceFactory

        # Simple and clean
        device = await AsyncDeviceFactory.create(
            "RX22",
            port="/dev/ttyAMA0"  # Raspberry Pi serial
        )

        # Use device
        info = await device.get_device_info()
        connected = await device.ping_request(timeout=3.0)
        await device.disconnect()
        ```
    """

    @staticmethod
    async def create(
        device_id: ASYNC_DEVICE_ID,
        port: str,
        timeout: float = 5.0,
        variant: str | None = None,
    ) -> AsyncBaseProtocol:
        """Create an async device instance.

        Args:
            device_id: Device type (e.g., "RX22", "RX09")
            port: Serial port path (e.g., "/dev/ttyAMA0")
            timeout: Default timeout for device operations
            variant: Device variant (optional, inferred from device_id)

        Returns:
            Async device instance ready to use

        Raises:
            ValueError: If device_id is unknown

        Example:
            ```python
            # RX22 on Raspberry Pi
            device = await AsyncDeviceFactory.create(
                "RX22",
                port="/dev/ttyAMA0",
                timeout=5.0
            )

            # RX11 USB
            device = await AsyncDeviceFactory.create(
                "RX11",
                port="/dev/ttyUSB0"
            )

            # RX09 ASCII protocol
            device = await AsyncDeviceFactory.create(
                "RX09",
                port="/dev/ttyUSB1"
            )
            ```
        """
        device_id_upper = device_id.upper()

        # Parse variant from device ID if present
        if variant is None and "-" in device_id_upper:
            _, variant = device_id_upper.split("-", 1)

        # Get device class
        device_class = _DEVICE_REGISTRY.get(device_id_upper)

        if device_class is None:
            supported = list(_DEVICE_REGISTRY.keys())
            raise ValueError(
                f"Unknown device: {device_id}. "
                f"Supported: {', '.join(sorted(set(d.split('-')[0] for d in supported)))}"
            )

        # Create device instance
        device = device_class(
            port=port,
            timeout=timeout,
            variant=variant,
        )

        # Connect to device
        try:
            if not await device.connect():
                raise RuntimeError(f"Failed to connect to {device_id} on {port}")
        except Exception as e:
            _LOGGER.error("Device connection error: %s", e)
            raise

        return device

    @staticmethod
    def get_supported_devices() -> list[str]:
        """Get list of supported device IDs.

        Returns:
            List of device type identifiers

        Example:
            ```python
            devices = AsyncDeviceFactory.get_supported_devices()
            # ['RX11', 'RX11-BASIC', 'RX11-EW', ..., 'RX09', 'RX09-BASIC']
            ```
        """
        return list(_DEVICE_REGISTRY.keys())

    @staticmethod
    def get_device_variants(device_id: str) -> list[str]:
        """Get variants for a specific device type.

        Args:
            device_id: Device type (e.g., "RX22")

        Returns:
            List of variant identifiers

        Example:
            ```python
            variants = AsyncDeviceFactory.get_device_variants("RX22")
            # ['BASIC', 'EW', 'DEV']  (and DEFAULT)
            ```
        """
        device_id_upper = device_id.upper()

        # Extract base device type
        if "-" in device_id_upper:
            base_type = device_id_upper.split("-")[0]
        else:
            base_type = device_id_upper

        # Find all variants for this base type
        variants = {k.split("-")[1] for k in _DEVICE_REGISTRY.keys() if k.startswith(base_type + "-")}

        return sorted(variants)
