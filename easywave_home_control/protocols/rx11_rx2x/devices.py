"""RxModule family device implementations.

Provides device classes for the RxModule protocol family:
- RX11: USB Transceiver
- RX21, RX22, RX25: Serial modules
"""

import logging
from typing import Any

from ...protocols.base import BaseProtocol
from .protocol import ErrorCode, RxModule

_LOGGER = logging.getLogger(__name__)


class RxModuleDevice(RxModule, BaseProtocol):
    """Base class for RxModule protocol family.

    Combines RxModule protocol with BaseProtocol interface.
    Subclasses specify device-specific parameters (baudrate, timing, etc.)
    """

    DEVICE_TYPE: str = "RX_BASE"
    DEFAULT_BAUDRATE: int = 115200
    ErrorCode = ErrorCode  # Expose ErrorCode as class attribute

    def __init__(
        self,
        port: str,
        timeout: float = 5.0,
    ) -> None:
        """Initialize RxModule device.

        Args:
            port: Serial port path
            timeout: Read timeout in seconds (stored but not used by RxModule)
        """
        self.port = port
        self.baudrate = self.DEFAULT_BAUDRATE  # Fixed at device default
        self.timeout = timeout

        # Initialize RxModule with device parameters
        RxModule.__init__(self, port=port, baudrate=self.baudrate)

    async def get_device_info(self) -> dict[str, Any]:
        """Get device information.

        Returns:
            Dictionary with device metadata
        """
        return {
            "device_type": self.DEVICE_TYPE,
            "port": self.port,
            "baudrate": self.baudrate,
            "connection_type": "USB Serial" if "USB" in self.DEVICE_TYPE else "Direct Serial UART",
        }

    async def get_available_functions(self) -> dict[str, str]:
        """Get available API functions.

        Returns:
            Dictionary of function names and descriptions
        """
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

    async def ping_request(self, timeout: float = 5.0) -> bool:
        """Ping RX Module device (required by BaseProtocol interface).

        Sends an intentionally undefined command (function code 0xF0) to the
        module.  The firmware replies with ERR_INVALID_REQUEST, which confirms
        the module is reachable.  Any ICP response is treated as success;
        only a timeout or a hardware/protocol error returns False.

        Args:
            timeout: Seconds to wait for the module's response.

        Returns:
            True  — module responded; serial link and firmware are healthy.
            False — no response (timeout) or hardware/protocol failure.
        """
        result = await self.ping(timeout)
        return result == 0

    async def disconnect(self) -> None:
        """Disconnect from device and close the serial connection."""
        await self.dispose()
        _LOGGER.info("RxModule disconnected from %s", self.port)


# Device type implementations


class RX11Device(RxModuleDevice):
    """EASYWAVE RX11 USB Transceiver."""

    DEVICE_TYPE = "RX11"
    DEFAULT_BAUDRATE = 115200


class RX21Device(RxModuleDevice):
    """EASYWAVE RX21 Serial Module (115200 bps)."""

    DEVICE_TYPE = "RX21"
    DEFAULT_BAUDRATE = 115200


class RX22Device(RxModuleDevice):
    """EASYWAVE RX22 Serial Module (115200 bps)."""

    DEVICE_TYPE = "RX22"
    DEFAULT_BAUDRATE = 115200


class RX25Device(RxModuleDevice):
    """EASYWAVE RX25 Serial Module (115200 bps)."""

    DEVICE_TYPE = "RX25"
    DEFAULT_BAUDRATE = 115200
