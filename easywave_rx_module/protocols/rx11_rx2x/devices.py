"""RxModule family device implementations.

Provides device classes for the RxModule protocol family:
- RX11: USB Transceiver
- RX21, RX22, RX25: Serial modules
"""

from typing import Any

from ...protocols.base import BaseProtocol
from .protocol import RxModule


class RxModuleDevice(RxModule, BaseProtocol):
    """Base class for RxModule protocol family.

    Combines RxModule protocol with BaseProtocol interface.
    Subclasses specify device-specific parameters (baudrate, timing, etc.)
    """

    DEVICE_TYPE: str = "RX_BASE"
    DEFAULT_BAUDRATE: int = 38400
    DEFAULT_VARIANT: str = "ew"

    def __init__(
        self,
        port: str,
        baudrate: int | None = None,
        timeout: float = 5.0,
        variant: str | None = None,
    ) -> None:
        """Initialize RxModule device.

        Args:
            port: Serial port path
            baudrate: Communication baudrate (defaults to device-specific)
            timeout: Read timeout in seconds (stored but not used by RxModule)
            variant: Protocol variant (ew, dev, basic, pro)
        """
        self.port = port
        self.baudrate = baudrate or self.DEFAULT_BAUDRATE
        self.timeout = timeout
        self.variant = variant or self.DEFAULT_VARIANT

        # Initialize RxModule with device parameters
        # Note: RxModule doesn't accept timeout parameter, it handles serial timeouts internally
        RxModule.__init__(self, port=port, baudrate=self.baudrate)
        BaseProtocol.__init__(
            self,
            port=port,
            device_type=self.DEVICE_TYPE,
            variant=self.variant,
        )

    def get_device_info(self) -> dict[str, Any]:
        """Get device information including variant.

        Returns:
            Dictionary with device metadata
        """
        return {
            "device_type": self.DEVICE_TYPE,
            "port": self.port,
            "baudrate": self.baudrate,
            "variant": self.variant,
            "connection_type": "USB Serial" if "USB" in self.DEVICE_TYPE else "Direct Serial UART",
        }

    def get_available_functions(self) -> dict[str, str]:
        """Get available API functions.

        Returns:
            Dictionary of function names and descriptions
        """
        # TODO: Implement variant-based function filtering
        # For now return all available functions
        return {
            # System functions
            "ping": "Ping device",
            "query_hw_version": "Query hardware version",
            "query_fw_version": "Query firmware version",
            # EasyWave Basic (EW)
            "ew_get_fd_serial_request": "Get EW serial number at index",
            "ew_rcv_button_request": "Receive EW button press",
            "ew_send_cmd_request": "Send EW command",
            "start_ew_send_cmd_loop": "Start continuous EW send command loop",
            "stop_ew_send_cmd_loop": "Stop continuous EW send command loop",
            "ew_rcv_ex_request": "Receive EW extended telegram",
            # EasyWave Bidi (EWB)
            "ewb_get_fd_serial_request": "Get EWB serial number at index",
            "ewb_add_nfilter_request": "Add EWB gateway to filter",
            "ewb_clear_nfilter_request": "Clear EWB filter",
            "ewb_join_device_request": "Join EWB device",
            "ewb_remove_device_request": "Remove EWB device",
            "ewb_rcv_request": "Receive EWB telegram",
            "ewb_change_state_request": "Change EWB device state",
            "ewb_query_state_request": "Query EWB device state",
            "ewb_tr_lrn_control_request": "Control EWB transmitter learning",
            # Secwave (SEC)
            "sec_rcv_request": "Receive Secwave security telegram",
            "sec_learn_request": "Learn/program Secwave security storage entry",
            "sec_stat_request": "Query Secwave security storage entry status",
            "sec_delete_request": "Delete Secwave security storage entry",
            "sec_delete_all_request": "Delete all Secwave security storage entries",
            "sec_reply_query_request": "Query Secwave security reply parameters",
            "sec_wr_userdata_request": "Write user data to Secwave security storage entry",
        }

    def ping_request(self, timeout: float = 5.0) -> bool:
        """Ping RX Module device (required by BaseProtocol interface).

        Args:
            timeout: Request timeout in seconds

        Returns:
            True if device responded successfully, False otherwise
        """
        result = self.ping(int(timeout))
        return result == 0


# Device type implementations

class RX11Device(RxModuleDevice):
    """EASYWAVE RX11 USB Transceiver."""

    DEVICE_TYPE = "RX11"
    DEFAULT_BAUDRATE = 38400


class RX21Device(RxModuleDevice):
    """EASYWAVE RX21 Serial Module (9600 bps)."""

    DEVICE_TYPE = "RX21"
    DEFAULT_BAUDRATE = 9600


class RX22Device(RxModuleDevice):
    """EASYWAVE RX22 Serial Module (9600 bps, enhanced)."""

    DEVICE_TYPE = "RX22"
    DEFAULT_BAUDRATE = 9600


class RX25Device(RxModuleDevice):
    """EASYWAVE RX25 Serial Module (38400 bps, high-speed)."""

    DEVICE_TYPE = "RX25"
    DEFAULT_BAUDRATE = 38400
