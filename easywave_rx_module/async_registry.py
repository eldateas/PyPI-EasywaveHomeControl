"""Async factory for creating EASYWAVE RX device instances.

Provides AsyncDeviceFactory.create() which returns async-enabled device
wrappers suitable for Home Assistant and other async frameworks.

This is the PRIMARY entry point for Home Assistant integration.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from .async_devices import AsyncDeviceBase, AsyncRxModuleDevice, AsyncRX09Device
from .protocols.rx09.devices import RX09Device
from .protocols.rx11_rx2x.devices import RX11Device, RX21Device, RX22Device, RX25Device
from .registry import DeviceRegistry

_LOGGER = logging.getLogger(__name__)

# Device type definitions
RX_DEVICE_ID = Literal[
    "RX11",
    "RX11-BASIC",
    "RX11-DEFAULT",
    "RX21",
    "RX21-BASIC",
    "RX21-DEFAULT",
    "RX22",
    "RX22-BASIC",
    "RX22-DEFAULT",
    "RX22-EW",
    "RX22-DEV",
    "RX25",
    "RX25-BASIC",
    "RX25-DEFAULT",
    "RX09",
    "RX09-BASIC",
]


class AsyncDeviceFactory:
    """Factory for creating async-enabled EASYWAVE RX devices.

    All devices created by this factory support async/await and will not
    block the event loop during serial I/O operations. This is the
    recommended API for Home Assistant integration.

    Example HA integration:
        ```python
        from easywave_rx_module import AsyncDeviceFactory

        # In HA async setup
        device = await AsyncDeviceFactory.create(
            "RX22",
            port="/dev/ttyAMA0",
            timeout=5.0
        )

        # Use async methods - never blocks
        info = await device.get_device_info()
        success = await device.ping_request(timeout=3.0)
        ```
    """

    @staticmethod
    async def create(
        device_id: RX_DEVICE_ID,
        port: str,
        timeout: float = 5.0,
        variant: str | None = None,
        executor: ThreadPoolExecutor | None = None,
    ) -> AsyncDeviceBase:
        """Create an async-enabled device instance.

        Args:
            device_id: Device type identifier (e.g., "RX22", "RX09")
            port: Serial port path (e.g., "/dev/ttyAMA0", "COM3")
            timeout: Request timeout in seconds (used as default for operations)
            variant: Protocol variant (e.g., "ew", "dev") - optional
            executor: Custom ThreadPoolExecutor for operations

        Returns:
            Async wrapper device instance (AsyncRxModuleDevice or AsyncRX09Device)

        Raises:
            ValueError: If device_id is unknown
            serial.SerialException: If port cannot be opened

        Example:
            ```python
            # RX22 on Raspberry Pi serial port
            device = await AsyncDeviceFactory.create(
                "RX22",
                port="/dev/ttyAMA0",
                timeout=10.0
            )

            # RX11 USB transceiver
            device = await AsyncDeviceFactory.create(
                "RX11",
                port="/dev/ttyUSB0"
            )

            # RX09 ASCII basic receiver
            device = await AsyncDeviceFactory.create(
                "RX09",
                port="/dev/ttyUSB1"
            )
            ```
        """
        loop = asyncio.get_event_loop()

        # Get the synchronous device class from registry
        device_class = DeviceRegistry.get_device_class(device_id)

        if device_class is None:
            available = DeviceRegistry.get_supported_devices()
            raise ValueError(
                f"Unknown device: {device_id}. "
                f"Supported devices: {', '.join(available)}"
            )

        # Create sync device in executor to avoid blocking
        def create_sync_device():
            return device_class(
                port=port,
                baudrate=None,  # Use device defaults
                timeout=timeout,
                variant=variant
            )

        sync_device = await loop.run_in_executor(None, create_sync_device)

        # Wrap in appropriate async wrapper
        if isinstance(sync_device, RX09Device):
            return AsyncRX09Device(sync_device, executor, loop)
        elif isinstance(sync_device, (RX11Device, RX21Device, RX22Device, RX25Device)):
            return AsyncRxModuleDevice(sync_device, executor, loop)
        else:
            raise TypeError(f"Unknown device type: {type(sync_device)}")

    @staticmethod
    def get_supported_devices() -> list[str]:
        """Get list of all supported device IDs.

        Returns:
            List of device ID strings

        Example:
            ```python
            devices = AsyncDeviceFactory.get_supported_devices()
            # ['RX11', 'RX21', 'RX22', 'RX25', 'RX09', ...]
            ```
        """
        return DeviceRegistry.get_supported_devices()

    @staticmethod
    def get_device_variants(device_id: str) -> list[str]:
        """Get available variants for a device.

        Args:
            device_id: Device type identifier (e.g., "RX22")

        Returns:
            List of variant strings (e.g., ["BASIC", "EW", "DEV"])

        Example:
            ```python
            variants = AsyncDeviceFactory.get_device_variants("RX22")
            # ["BASIC", "EW", "DEV", "DEFAULT"]
            ```
        """
        all_variants = DeviceRegistry.get_supported_variants()
        device_id_upper = device_id.upper()
        
        # Remove variant suffix if present (e.g., "RX22-EW" -> "RX22")
        if "-" in device_id_upper:
            device_id_upper = device_id_upper.split("-")[0]
        
        return all_variants.get(device_id_upper, [])
