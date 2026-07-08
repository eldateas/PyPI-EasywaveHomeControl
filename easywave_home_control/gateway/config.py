"""Configuration for transceiver gateways."""

from __future__ import annotations

from dataclasses import dataclass, field

# ELDAT RX11 USB Transceiver (VID 0x155A, PID 0x1014)
DEFAULT_RX11_USB_IDS: frozenset[tuple[int, int]] = frozenset({(0x155A, 0x1014)})


@dataclass(slots=True)
class GatewayConfig:
    """Connection-management settings for a transceiver gateway."""

    transceiver_id: str = "RX11"
    """Transceiver profile id (RX11, RX21, RX22, RX25, RX09, or a registered successor)."""

    port: str | None = None
    """Serial device path. When ``None``, USB discovery uses ``usb_ids``."""

    usb_ids: frozenset[tuple[int, int]] = field(default_factory=lambda: DEFAULT_RX11_USB_IDS)
    """Supported ``(vid, pid)`` pairs for automatic USB discovery (typically RX11)."""

    baudrate: int = 115200

    settle_seconds: float = 1.5
    """Delay after opening the serial port before version queries."""

    health_check_interval: float = 30.0
    health_check_max_failures: int = 3

    reconnect_interval: float = 30.0
    """Delay between reconnect attempts when ``auto_reconnect`` is enabled."""

    reconnect_min_delay_after_disconnect: float = 1.0
    """Minimum wait after disconnect before the next connect attempt."""

    version_query_retries: int = 3
    version_query_retry_delay: float = 0.5

    auto_reconnect: bool = True
    """When enabled, keep trying to reconnect after connection loss."""

    auto_listen: bool = False
    """Start a background EW_RCV_EX listener and invoke ``on_telegram``."""

    listen_timeout: float = 30.0
    request_timeout: float = 5.0
