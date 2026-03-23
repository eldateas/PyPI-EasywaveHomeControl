"""Device registry and factory for EASYWAVE modules.

Central registry for all supported device types.
Enables string-based device creation: "RX11", "RX25", etc.
"""

from typing import Any

from .protocols.base import BaseProtocol
from .protocols.rx09 import RX09Device
from .protocols.rx11_rx2x import (
    RX11Device,
    RX21Device,
    RX22Device,
    RX25Device,
)


class DeviceRegistry:
    """Registry of supported device types and their factories.

    Example: "RX11" -> RX11Device
    """

    _REGISTRY: dict[str, type] = {
        # RxModule family - RX11, RX21, RX22, RX25
        "RX11": RX11Device,
        "RX21": RX21Device,
        "RX22": RX22Device,
        "RX25": RX25Device,
        # RX09 family (ASCII text protocol)
        "RX09": RX09Device,
    }

    @classmethod
    def register(cls, device_id: str, device_class: type[BaseProtocol]) -> None:
        """Register a device type.

        Args:
            device_id: Device identifier (e.g., "RX11-EW", "RX09-V1")
            device_class: Device class to instantiate
        """
        cls._REGISTRY[device_id.upper()] = device_class

    @classmethod
    def get(cls, device_id: str) -> type[BaseProtocol] | None:
        """Get device class for a device ID.

        Args:
            device_id: Device identifier (e.g., "RX11-EW")

        Returns:
            Device class or None if not registered
        """
        return cls._REGISTRY.get(device_id.upper())

    @classmethod
    def get_device_class(cls, device_id: str) -> type[BaseProtocol] | None:
        """Alias for get() - used by async_registry for consistency.

        Args:
            device_id: Device identifier (e.g., "RX11-EW")

        Returns:
            Device class or None if not registered
        """
        return cls.get(device_id)

    @classmethod
    def list(cls) -> list[str]:
        """List all registered device IDs.

        Returns:
            List of device identifiers
        """
        return list(cls._REGISTRY.keys())


class DeviceFactory:
    """Factory for creating EASYWAVE devices.

    Example:
        >>> device = DeviceFactory.create("RX11", port="/dev/ttyUSB0")
        >>> device.ping_request()
        >>>
        >>> available = device.get_available_functions()
        >>> print(f"RX11 supports: {list(available.keys())}")
    """

    @classmethod
    def create(
        cls,
        device_id: str,
        port: str,
        timeout: float = 5.0,
        **kwargs: Any,
    ) -> BaseProtocol:
        """Create a device instance.

        Args:
            device_id: Device identifier (e.g., "RX11", "RX25")
            port: Serial port path (e.g., "/dev/ttyUSB0")
            timeout: Read timeout in seconds (default: 5.0)
            **kwargs: Additional device-specific parameters

        Returns:
            Initialized device instance

        Raises:
            ValueError: If device_id is not registered
            serial.SerialException: If port cannot be opened
            OSError: If port is invalid

        Example:
            >>> # Create RX11
            >>> device = DeviceFactory.create("RX11", port="/dev/ttyUSB0")
            >>>
            >>> # Create RX25
            >>> device = DeviceFactory.create("RX25", port="/dev/ttyAMA0", timeout=10.0)
        """
        device_id_upper = device_id.upper()

        # Get device class from registry
        device_class = DeviceRegistry.get(device_id_upper)

        if device_class is None:
            supported = DeviceRegistry.list()
            raise ValueError(f"Unknown device ID: {device_id}. Supported types: {supported}")

        # Create device instance
        device = device_class(port=port, timeout=timeout, **kwargs)  # type: ignore[call-arg]

        return device

    @classmethod
    def get_supported_devices(cls) -> list[str]:
        """Get list of all supported device IDs.

        Returns:
            List of device identifiers
        """
        return DeviceRegistry.list()

    @classmethod
    def register_device(
        cls,
        device_id: str,
        device_class: type[BaseProtocol],
    ) -> None:
        """Register a custom device type.

        Allows extending the library with new device families.

        Args:
            device_id: Device identifier (e.g., "RX09-V1", "CUSTOM-DEV")
            device_class: Class inheriting from BaseProtocol

        Example:
            >>> class CustomDevice(BaseProtocol):
            ...     def get_device_info(self):
            ...         return {"device_type": "CUSTOM"}
            ...     def get_available_functions(self):
            ...         return {"ping": "Custom ping"}
            ...     def ping_request(self):
            ...         return True
            >>>
            >>> DeviceFactory.register_device("CUSTOM-V1", CustomDevice)
            >>> device = DeviceFactory.create("CUSTOM-V1", port="/dev/ttyUSB0")
        """
        DeviceRegistry.register(device_id, device_class)
