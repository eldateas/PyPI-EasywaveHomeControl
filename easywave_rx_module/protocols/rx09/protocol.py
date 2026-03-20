"""RX09 Protocol Implementation.

RX09 (RTR09) is an Easywave Basic only device with a completely different protocol:
- ASCII text-based (not binary)
- Comma-separated commands
- CR (0x0D) line terminator
- 57600 baud (not 38400)
- Very simple command set (~10 commands vs. 40+ for RxModule)

This protocol does NOT support:
- EasyWave Bidi (EWB)
- Secwave (SEC)
- Variants (only basic Easywave)

Reference: Specification "Spezifikation RTR09" from ELDAT GmbH (2009-08-18)
"""

import logging
import serial
import threading
import time
from typing import Any

from ...protocols.base import BaseProtocol

_LOGGER = logging.getLogger(__name__)


class RX09Protocol(BaseProtocol):
    """RX09 Protocol Handler (ASCII Text-based Easywave Basic)."""

    DEVICE_TYPE = "RX09"
    DEFAULT_BAUDRATE = 57600

    def __init__(
        self,
        port: str,
        baudrate: int | None = None,
        timeout: float = 5.0,
        variant: str | None = None,
    ) -> None:
        """Initialize RX09 device.

        Args:
            port: Serial port path (e.g., '/dev/ttyUSB0', 'COM3')
            baudrate: Communication baudrate (defaults to 57600)
            timeout: Read timeout in seconds
            variant: Protocol variant (reserved for future use)
        """
        self.port = port
        self.baudrate = baudrate or self.DEFAULT_BAUDRATE
        self.timeout = timeout
        self.variant = variant or "basic"

        # Initialize BaseProtocol
        BaseProtocol.__init__(
            self,
            port=port,
            device_type=self.DEVICE_TYPE,
            variant=self.variant,
        )

        # Serial connection
        self._serial = None
        self._serial_lock = threading.RLock()
        self._connected = False

        # Device info cache
        self._device_id = None
        self._device_version = None
        self._vendor_id = None
        self._device_num_positions = None

        # Health monitoring
        self._last_activity = time.time()
        self._health_check_thread = None
        self._health_check_running = False

    def _open_serial(self) -> bool:
        """Open and configure serial port."""
        try:
            if self._serial and self._serial.is_open:
                return True

            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )
            self._connected = True
            _LOGGER.info("RX09: Opened serial port %s at %d baud", self.port, self.baudrate)
            return True
        except serial.SerialException as e:
            _LOGGER.error("RX09: Failed to open serial port: %s", e)
            self._connected = False
            return False

    def _close_serial(self) -> None:
        """Close serial port."""
        try:
            with self._serial_lock:
                if self._serial and self._serial.is_open:
                    self._serial.close()
                    self._connected = False
                    _LOGGER.info("RX09: Closed serial port")
        except Exception as e:
            _LOGGER.error("RX09: Error closing serial port: %s", e)

    def _escape_string(self, data: str) -> str:
        """Escape special characters in data.

        In RX09 protocol:
        - Comma (,) must be escaped as \\,
        - Backslash (\\) must be escaped as \\\\
        """
        data = data.replace("\\", "\\\\")  # Backslash first
        data = data.replace(",", "\\,")
        return data

    def _unescape_string(self, data: str) -> str:
        """Unescape special characters in received data."""
        data = data.replace("\\,", ",")
        data = data.replace("\\\\", "\\")
        return data

    def _send_command(self, command: str) -> bool:
        """Send a command to the device.

        Args:
            command: Command string (without CR)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            with self._serial_lock:
                if not self._connected or not self._serial or not self._serial.is_open:
                    if not self._open_serial():
                        return False

                # Send command with CR terminator
                data = (command + "\r").encode("ascii")
                self._serial.write(data)
                self._last_activity = time.time()
                _LOGGER.debug("RX09: Sent command: %s", command)
                return True
        except Exception as e:
            _LOGGER.error("RX09: Error sending command: %s", e)
            self._connected = False
            return False

    def _read_response(self, timeout: float | None = None) -> str | None:
        """Read a response line from the device.

        Returns:
            Response string (without CR), or None on timeout/error
        """
        try:
            with self._serial_lock:
                if not self._connected or not self._serial or not self._serial.is_open:
                    if not self._open_serial():
                        return None

                timeout_val = timeout or self.timeout
                self._serial.timeout = timeout_val

                # Read until CR (0x0D)
                line = b""
                start = time.time()
                while True:
                    ch = self._serial.read(1)
                    if not ch:
                        if time.time() - start > timeout_val:
                            _LOGGER.debug("RX09: Read timeout")
                            return None
                        continue

                    if ch == b"\r":
                        break
                    line += ch

                response = line.decode("ascii", errors="ignore").strip()
                self._last_activity = time.time()
                _LOGGER.debug("RX09: Received response: %s", response)
                return response
        except Exception as e:
            _LOGGER.error("RX09: Error reading response: %s", e)
            self._connected = False
            return None

    def _send_and_receive(self, command: str, timeout: float | None = None) -> str | None:
        """Send command and wait for response.

        Args:
            command: Command to send
            timeout: Response timeout (uses default if None)

        Returns:
            Response string, or None on error
        """
        if not self._send_command(command):
            return None

        response = self._read_response(timeout)
        if response in ["OK", "ERROR"]:
            return response
        return response

    # ================================================================================================
    # BASEPROTOCOL INTERFACE
    # ================================================================================================

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
            "connection_type": "USB Serial",
            "protocol": "ASCII Text-based",
        }

    def get_available_functions(self) -> dict[str, str]:
        """Get available API functions.

        RX09 only supports basic Easywave functions (no Bidi, no Secwave).

        Returns:
            Dictionary of function names and descriptions
        """
        return {
            # System functions
            "ping": "Ping device (query device ID)",
            "get_device_id": "Get device identification",
            "query_positions": "Query number of transmitter positions (channels)",
            # Position management
            "read_position_data": "Read 22-bit serial number at position",
            # Transmit
            "send_telegramm": "Send telegramm from position with button code",
            # Receive (unsolicited)
            "receive_telegramm": "Receive incoming telegramm (unsolicited)",
            # Status
            "query_echo": "Query ECHO status",
            "set_echo": "Enable/disable ECHO",
            "query_led": "Query LED status",
            "set_led": "Control red LED",
            "query_button": "Query button status (pressed/released)",
        }

    def ping(self, duration: int = 5) -> int:
        """Ping the device by querying device ID.

        Args:
            duration: Unused (kept for interface compatibility)

        Returns:
            0 (SUCCESS) on success, non-zero error code otherwise
        """
        response = self._send_and_receive("ID?", timeout=duration)
        if response and response != "ERROR":
            # Parse: ID,VendorID,DeviceID,Version
            parts = response.split(",")
            if len(parts) >= 4:
                return 0  # SUCCESS
        return 1  # ERROR

    def ping_request(self, timeout: float = 5.0) -> bool:
        """Ping RX09 device (required by BaseProtocol interface).

        Args:
            timeout: Request timeout in seconds

        Returns:
            True if device responded successfully, False otherwise
        """
        result = self.ping(int(timeout))
        return result == 0

    # ================================================================================================
    # RX09 SPECIFIC API FUNCTIONS
    # ================================================================================================

    def get_device_id(self, timeout: float = 5.0) -> tuple[int, int | None, int | None, int | None]:
        """Get device identification.

        Args:
            timeout: Request timeout

        Returns:
            (result, vendor_id, device_id, version) or (ERROR, None, None, None)
        """
        response = self._send_and_receive("ID?", timeout=timeout)
        if not response or response == "ERROR":
            return 1, None, None, None

        try:
            parts = response.split(",")
            if len(parts) >= 4:
                vendor_id = int(parts[1], 16)
                device_id = int(parts[2], 16)
                device_version = int(parts[3], 16)
                self._device_id = device_id
                self._vendor_id = vendor_id
                self._device_version = device_version
                return 0, vendor_id, device_id, device_version
        except (ValueError, IndexError) as e:
            _LOGGER.error("RX09: Failed to parse device ID: %s", e)

        return 1, None, None, None

    def query_positions(self, timeout: float = 5.0) -> tuple[int, int | None]:
        """Query number of transmitter positions (channels).

        Args:
            timeout: Request timeout

        Returns:
            (result, num_positions) or (ERROR, None)
        """
        response = self._send_and_receive("GETP?", timeout=timeout)
        if not response or response == "ERROR":
            return 1, None

        try:
            parts = response.split(",")
            if len(parts) >= 2:
                num_positions = int(parts[1], 16)
                self._device_num_positions = num_positions
                return 0, num_positions
        except (ValueError, IndexError) as e:
            _LOGGER.error("RX09: Failed to parse positions: %s", e)

        return 1, None

    def read_position_data(
        self, position: int, timeout: float = 5.0
    ) -> tuple[int, int | None]:
        """Read 22-bit serial number at position.

        Args:
            position: Position index (0-255)
            timeout: Request timeout

        Returns:
            (result, serial_number) or (ERROR, None)
        """
        command = f"RDP?,{position:02x}"
        response = self._send_and_receive(command, timeout=timeout)
        if not response or response == "ERROR":
            return 1, None

        try:
            parts = response.split(",")
            if len(parts) >= 3:
                serial_number = int(parts[2], 16)
                return 0, serial_number
        except (ValueError, IndexError) as e:
            _LOGGER.error("RX09: Failed to parse position data: %s", e)

        return 1, None

    def send_telegramm(
        self, position: int, button: str, timeout: float = 5.0
    ) -> int:
        """Send telegramm from position with button code.

        Args:
            position: Position index (0-255)
            button: Button code ('A', 'B', 'C', or 'D')
            timeout: Request timeout

        Returns:
            0 (SUCCESS) on success, non-zero error code otherwise
        """
        if button not in ["A", "B", "C", "D"]:
            _LOGGER.error("RX09: Invalid button code: %s", button)
            return 1

        command = f"TXP,{position:02x},{button}"
        response = self._send_and_receive(command, timeout=timeout)
        return 0 if response == "OK" else 1

    def receive_telegramm(self, timeout: float = 30.0) -> tuple[int, int | None, str | None]:
        """Receive incoming telegramm (unsolicited).

        Args:
            timeout: Receive timeout

        Returns:
            (result, serial_number, button_code) or (ERROR, None, None)
        """
        response = self._read_response(timeout)
        if not response or response == "ERROR":
            return 1, None, None

        try:
            parts = response.split(",")
            if len(parts) >= 3 and parts[0] == "REC":
                serial_number = int(parts[1], 16)
                button_code = parts[2]
                if button_code in ["A", "B", "C", "D"]:
                    return 0, serial_number, button_code
        except (ValueError, IndexError) as e:
            _LOGGER.error("RX09: Failed to parse received telegramm: %s", e)

        return 1, None, None

    # ================================================================================================
    # STATUS AND CONTROL FUNCTIONS
    # ================================================================================================

    def query_echo(self, timeout: float = 5.0) -> tuple[int, bool | None]:
        """Query ECHO status.

        Args:
            timeout: Request timeout

        Returns:
            (result, is_on) or (ERROR, None)
        """
        response = self._send_and_receive("ECHO?", timeout=timeout)
        if not response or response == "ERROR":
            return 1, None

        if "ON" in response:
            return 0, True
        elif "OFF" in response:
            return 0, False

        return 1, None

    def set_echo(self, enabled: bool, timeout: float = 5.0) -> int:
        """Enable/disable ECHO.

        Args:
            enabled: True to enable, False to disable
            timeout: Request timeout

        Returns:
            0 (SUCCESS) on success, non-zero error code otherwise
        """
        cmd = "ON" if enabled else "OFF"
        command = f"ECHO,{cmd}"
        response = self._send_and_receive(command, timeout=timeout)
        return 0 if response == "OK" else 1

    def query_led(self, timeout: float = 5.0) -> tuple[int, bool | None]:
        """Query LED status.

        Args:
            timeout: Request timeout

        Returns:
            (result, is_on) or (ERROR, None)
        """
        response = self._send_and_receive("LED?", timeout=timeout)
        if not response or response == "ERROR":
            return 1, None

        if "ON" in response:
            return 0, True
        elif "OFF" in response:
            return 0, False

        return 1, None

    def set_led(self, enabled: bool, timeout: float = 5.0) -> int:
        """Control red LED.

        Args:
            enabled: True to turn on, False to turn off
            timeout: Request timeout

        Returns:
            0 (SUCCESS) on success, non-zero error code otherwise
        """
        cmd = "ON" if enabled else "OFF"
        command = f"LED,{cmd}"
        response = self._send_and_receive(command, timeout=timeout)
        return 0 if response == "OK" else 1

    def query_button(self, timeout: float = 5.0) -> tuple[int, bool | None]:
        """Query button status (pressed/released).

        Args:
            timeout: Request timeout

        Returns:
            (result, is_pressed) or (ERROR, None)
        """
        response = self._send_and_receive("BUTTON?", timeout=timeout)
        if not response or response == "ERROR":
            return 1, None

        if "pressed" in response:
            return 0, True
        elif "released" in response:
            return 0, False

        return 1, None

    def __del__(self) -> None:
        """Cleanup on object destruction."""
        self._close_serial()
