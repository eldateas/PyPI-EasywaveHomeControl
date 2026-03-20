"""Abstract protocol base class for EASYWAVE devices.

All device protocols inherit from BaseProtocol to provide a common interface.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseProtocol(ABC):
    """Abstract base class for EASYWAVE device protocols.

    Different device families (RxModule, RX09, etc.) implement this interface
    to provide a consistent way for applications (like Home Assistant) to interact
    with devices regardless of their underlying protocol.

    Attributes:
        port: Serial/communication port identifier
        device_type: Device identifier (e.g., "RX11", "RX09")
        variant: Protocol variant if supported (e.g., "ew", "dev")
    """

    def __init__(
        self,
        port: str,
        device_type: str,
        variant: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize protocol.

        Args:
            port: Communication port path
            device_type: Device type identifier
            variant: Optional protocol variant (e.g., "ew", "dev")
            *args: Protocol-specific positional arguments
            **kwargs: Protocol-specific keyword arguments
        """
        self.port = port
        self.device_type = device_type
        self.variant = variant or "default"

    @abstractmethod
    def get_device_info(self) -> dict[str, Any]:
        """Get device information.

        Returns:
            Dictionary with device metadata (type, port, variant, etc.)
        """
        pass

    @abstractmethod
    def get_available_functions(self) -> dict[str, str]:
        """Get available API functions for this device and variant.

        Returns:
            Dictionary mapping function names to descriptions
            e.g., {"ping": "Ping device", "ew_send_cmd": "Send EasyWave command"}
        """
        pass

    @abstractmethod
    def ping_request(self, timeout: float = 1.0) -> bool:
        """Ping device to check connectivity.

        Args:
            timeout: Request timeout in seconds

        Returns:
            True if device responded, False otherwise
        """
        pass
