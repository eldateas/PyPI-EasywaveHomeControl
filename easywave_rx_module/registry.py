"""Device registry and factory for EASYWAVE modules.

Central registry for all device types and variants.
Enables string-based device creation: "RX11-EW", "RX25-DEV", etc.
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

    Format: "DEVICE_TYPE-VARIANT" -> Device class
    Example: "RX11-EW" -> RX11Device with ew variant
    """

    _REGISTRY: dict[str, type] = {
        # RxModule family - RX11
        "RX11": RX11Device,
        "RX11-BASIC": RX11Device,
        "RX11-EW": RX11Device,
        "RX11-DEV": RX11Device,
        # RxModule family - RX21
        "RX21": RX21Device,
        "RX21-BASIC": RX21Device,
        "RX21-EW": RX21Device,
        "RX21-DEV": RX21Device,
        # RxModule family - RX22
        "RX22": RX22Device,
        "RX22-BASIC": RX22Device,
        "RX22-EW": RX22Device,
        "RX22-DEV": RX22Device,
        # RxModule family - RX25
        "RX25": RX25Device,
        "RX25-BASIC": RX25Device,
        "RX25-EW": RX25Device,
        "RX25-DEV": RX25Device,
        # RX09 family (ASCII text protocol, basic Easywave only)
        "RX09": RX09Device,
        "RX09-BASIC": RX09Device,
    }

    @classmethod
    def register(cls, device_id: str, device_class: type[BaseProtocol]) -> None:
        """Register a device type.

        Args:
            device_id: Device identifier (e.g., "RX11-EW", "RX09-V1")
            device_class: Device class to instantiate

        Raises:
            TypeError: If device_class is not a BaseProtocol subclass
        """
        if not issubclass(device_class, BaseProtocol):
            raise TypeError(f"device_class must be a BaseProtocol subclass, got {device_class}")

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

    @classmethod
    def get_supported_variants(cls) -> dict[str, list[str]]:
        """Get all supported device types and their variants.

        Returns:
            Dictionary mapping device types to variant list
            e.g., {"RX11": ["BASIC", "EW", "DEV"], "RX25": [...]}
        """
        variants: dict[str, list[str]] = {}

        for device_id in cls._REGISTRY.keys():
            if "-" in device_id:
                device_type, variant = device_id.split("-", 1)
            else:
                device_type = device_id
                variant = "DEFAULT"

            if device_type not in variants:
                variants[device_type] = []

            if variant not in variants[device_type]:
                variants[device_type].append(variant)

        return variants


class DeviceFactory:
    """Factory for creating EASYWAVE devices.

    Supports string-based device creation with variants:
    - "RX11" or "RX11-DEFAULT" (uses DEFAULT_VARIANT)
    - "RX11-EW" (EasyWave variant)
    - "RX11-DEV" (Developer variant)
    - "RX25-BASIC" (Basic variant)

    Example:
        >>> device = DeviceFactory.create("RX11-EW", port="/dev/ttyUSB0")
        >>> device.ping_request()
        >>>
        >>> available = device.get_available_functions()
        >>> print(f"RX11-EW supports: {list(available.keys())}")
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
            device_id: Device identifier (e.g., "RX11-EW", "RX25-DEV")
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
            >>> # Create RX11 with EasyWave variant
            >>> device = DeviceFactory.create("RX11-EW", port="/dev/ttyUSB0")
            >>>
            >>> # Create RX25 with developer variant
            >>> device = DeviceFactory.create("RX25-DEV", port="/dev/ttyAMA0", timeout=10.0)
        """
        device_id_upper = device_id.upper()

        # Parse variant from device ID (format: "DEVICE-VARIANT")
        variant: str | None = None
        if "-" in device_id_upper:
            _, variant = device_id_upper.split("-", 1)

        # Get device class from registry
        device_class = DeviceRegistry.get(device_id_upper)

        if device_class is None:
            supported = DeviceRegistry.list()
            raise ValueError(f"Unknown device ID: {device_id}. " f"Supported types: {supported}")

        # Create device instance with variant
        device = device_class(port=port, timeout=timeout, variant=variant, **kwargs)

        return device

    @classmethod
    def get_supported_devices(cls) -> list[str]:
        """Get list of all supported device IDs.

        Returns:
            List of device identifiers
        """
        return DeviceRegistry.list()

    @classmethod
    def get_device_variants(cls) -> dict[str, list[str]]:
        """Get all supported device types and their variants.

        Returns:
            Dictionary mapping device types to variant list

        Example:
            >>> variants = DeviceFactory.get_device_variants()
            >>> print(variants)
            {'RX11': ['BASIC', 'EW', 'DEV', 'DEFAULT'],
             'RX21': ['BASIC', 'EW', 'DEV', 'DEFAULT'],
             ...}
        """
        return DeviceRegistry.get_supported_variants()

    @classmethod
    def get_variant_info(cls, variant: str) -> dict[str, str]:
        """Get available functions for a variant.

        Note: Variant filtering is not yet implemented.

        Args:
            variant: Variant name (e.g., "ew", "dev", "basic")

        Returns:
            Dictionary of available functions and descriptions

        Raises:
            NotImplementedError: Variant system not yet implemented
        """
        raise NotImplementedError(
            "Variant filtering not yet implemented. "
            "All devices currently support the full RxModule API."
        )

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
