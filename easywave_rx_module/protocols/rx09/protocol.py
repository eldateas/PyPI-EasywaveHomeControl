"""Async RX09 Protocol Implementation.

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

Pure async implementation using asyncio.

Reference: Specification "Spezifikation RTR09" from ELDAT GmbH (2009-08-18)
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from enum import IntEnum
from typing import Any

from ...protocols.base import BaseProtocol

_LOGGER = logging.getLogger(__name__)


class ErrorCode(IntEnum):
    """Error codes for RX09 ASCII protocol operations."""

    SUCCESS = 0x00
    ERR_INVALID_COMMAND = 0x01
    ERR_INVALID_POSITION = 0x02
    ERR_SERIAL_NOT_FOUND = 0x03
    ERR_TIMEOUT = 0x04
    ERR_INVALID_PARAMETER = 0x05
    ERR_DEVICE_ERROR = 0xFF


class RX09Protocol(BaseProtocol):
    """Pure async RX09 Protocol Handler (ASCII Text-based Easywave Basic)."""

    DEVICE_TYPE = "RX09"
    BAUDRATE = 57600  # Fixed at 57600
    DEFAULT_TIMEOUT = 5.0

    def __init__(
        self,
        port: str,
        timeout: float = 5.0,
        variant: str | None = None,
    ) -> None:
        """Initialize RX09 device.

        Args:
            port: Serial port path (e.g., '/dev/ttyUSB0', 'COM3')
            timeout: Read timeout in seconds
            variant: Protocol variant (reserved for future use)
        """
        self.port = port
        self.baudrate = self.BAUDRATE
        self.timeout = timeout
        self.variant = variant or "basic"

        # Async serial connection
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connected = False

        # Locks
        self._lock = asyncio.Lock()

        # Tasks
        self._reader_task: asyncio.Task[None] | None = None

        # State
        self._shutdown_requested = False

        # Device info cache
        self._device_id = None
        self._device_version = None
        self._vendor_id = None
        self._device_num_positions = None

        # Callback system for spontaneous RCV messages
        self._rcv_callbacks: list[Callable[[dict[str, Any]], None | object]] = []
        self._callback_lock = asyncio.Lock()

    async def connect(self) -> bool:
        """Connect to RX09 device.

        Returns:
            True if connected successfully
        """
        try:
            _LOGGER.debug("Connecting RX09 to %s", self.port)
            # Real implementation would use serial_asyncio
            # import serial_asyncio
            # self._reader, self._writer = await serial_asyncio.open_serial_connection(
            #     url=self.port, baudrate=self.BAUDRATE
            # )
            self._connected = True

            # Start background reader task
            self._reader_task = asyncio.create_task(self._reader_loop())

            _LOGGER.info("RX09 connected to %s", self.port)
            return True
        except Exception as e:
            _LOGGER.error("RX09 connection failed: %s", e)
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from device and clear all callbacks."""
        self._shutdown_requested = True

        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass

        # Clear callbacks
        async with self._callback_lock:
            self._rcv_callbacks.clear()

        self._connected = False
        _LOGGER.info("RX09 disconnected")

    # ================================================================================================
    # BASEPROTOCOL INTERFACE
    # ================================================================================================

    async def get_device_info(self) -> dict[str, Any]:
        """Get device information including variant.

        Returns:
            Dictionary with device metadata
        """
        return {
            "device_type": self.DEVICE_TYPE,
            "port": self.port,
            "baudrate": self.BAUDRATE,
            "variant": self.variant,
            "connection_type": "USB Serial",
            "protocol": "ASCII Text-based (Easywave Basic only)",
        }

    async def get_available_functions(self) -> dict[str, str]:
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

    async def ping_request(self, timeout: float = 5.0) -> bool:
        """Ping RX09 device (required by BaseProtocol interface).

        Args:
            timeout: Request timeout in seconds

        Returns:
            True if device responded successfully, False otherwise
        """
        result = await self.ping(int(timeout))
        return result == 0

    # ================================================================================================
    # RX09 SPECIFIC API FUNCTIONS
    # ================================================================================================

    async def ping(self, timeout: float = 5.0) -> int:
        """Ping the device by querying device ID.

        Args:
            timeout: Timeout in seconds

        Returns:
            0 (SUCCESS) on success, non-zero error code otherwise
        """
        response = await self._send_and_receive("ID?", timeout=timeout)
        if response and response != "ERROR":
            # Parse: ID,VendorID,DeviceID,Version
            parts = response.split(",")
            if len(parts) >= 4:
                return 0  # SUCCESS
        return 1  # ERROR

    async def get_device_id(
        self, timeout: float = 5.0
    ) -> tuple[int, int | None, int | None, int | None]:
        """Get device identification.

        Args:
            timeout: Request timeout

        Returns:
            (result, vendor_id, device_id, version) or (ERROR, None, None, None)
        """
        response = await self._send_and_receive("ID?", timeout=timeout)
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

    async def query_positions(self, timeout: float = 5.0) -> tuple[int, int | None]:
        """Query number of transmitter positions (channels).

        Args:
            timeout: Request timeout

        Returns:
            (result, num_positions) or (ERROR, None)
        """
        response = await self._send_and_receive("GETP?", timeout=timeout)
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

    async def read_position_data(
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
        response = await self._send_and_receive(command, timeout=timeout)
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

    async def send_telegramm(self, position: int, button: str, timeout: float = 5.0) -> int:
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
        response = await self._send_and_receive(command, timeout=timeout)
        return 0 if response == "OK" else 1

    async def receive_telegramm(self, timeout: float | None = 30.0) -> tuple[int, int | None, str | None]:
        """Receive incoming telegramm (unsolicited).

        Args:
            timeout: Receive timeout in seconds. Use None for indefinite waiting.

        Returns:
            (result, serial_number, button_code) or (ERROR, None, None)
        """
        try:
            # This waits for unsolicited reception using background reader
            if timeout is None:
                # Indefinite waiting (no timeout)
                result = await self._wait_for_rcv_message()
            else:
                # Timed waiting
                result = await asyncio.wait_for(self._wait_for_rcv_message(), timeout=timeout)

            if result:
                return 0, result.get("serial_number"), result.get("button_code")
            return 1, None, None
        except asyncio.TimeoutError:
            _LOGGER.debug("Receive telegramm timeout after %.1f seconds", timeout)
            return 1, None, None
        except Exception as e:
            _LOGGER.error("Receive telegramm error: %s", e)
            return 1, None, None

    async def query_echo(self, timeout: float = 5.0) -> tuple[int, bool | None]:
        """Query ECHO status.

        Args:
            timeout: Request timeout

        Returns:
            (result, is_on) or (ERROR, None)
        """
        response = await self._send_and_receive("ECHO?", timeout=timeout)
        if not response or response == "ERROR":
            return 1, None

        if "ON" in response:
            return 0, True
        elif "OFF" in response:
            return 0, False

        return 1, None

    async def set_echo(self, enabled: bool, timeout: float = 5.0) -> int:
        """Enable/disable ECHO.

        Args:
            enabled: True to enable, False to disable
            timeout: Request timeout

        Returns:
            0 (SUCCESS) on success, non-zero error code otherwise
        """
        cmd = "ON" if enabled else "OFF"
        command = f"ECHO,{cmd}"
        response = await self._send_and_receive(command, timeout=timeout)
        return 0 if response == "OK" else 1

    async def query_led(self, timeout: float = 5.0) -> tuple[int, bool | None]:
        """Query LED status.

        Args:
            timeout: Request timeout

        Returns:
            (result, is_on) or (ERROR, None)
        """
        response = await self._send_and_receive("LED?", timeout=timeout)
        if not response or response == "ERROR":
            return 1, None

        if "ON" in response:
            return 0, True
        elif "OFF" in response:
            return 0, False

        return 1, None

    async def set_led(self, enabled: bool, timeout: float = 5.0) -> int:
        """Control red LED.

        Args:
            enabled: True to turn on, False to turn off
            timeout: Request timeout

        Returns:
            0 (SUCCESS) on success, non-zero error code otherwise
        """
        cmd = "ON" if enabled else "OFF"
        command = f"LED,{cmd}"
        response = await self._send_and_receive(command, timeout=timeout)
        return 0 if response == "OK" else 1

    async def query_button(self, timeout: float = 5.0) -> tuple[int, bool | None]:
        """Query button status (pressed/released).

        Args:
            timeout: Request timeout

        Returns:
            (result, is_pressed) or (ERROR, None)
        """
        response = await self._send_and_receive("BUTTON?", timeout=timeout)
        if not response or response == "ERROR":
            return 1, None

        if "pressed" in response:
            return 0, True
        elif "released" in response:
            return 0, False

        return 1, None

    # ================================================================================================
    # CALLBACK SUPPORT FOR SPONTANEOUS RCV MESSAGES
    # ================================================================================================

    def register_rcv_callback(self, callback: Callable[[dict[str, Any]], None | object]) -> None:
        """Register a callback for spontaneous RCV (receive) messages.

        The callback will be invoked asynchronously when a RCV message is received.

        Args:
            callback: Async or sync callable that receives a dictionary with:
                - serial_number (int): 22-bit serial number (hex from device)
                - button_code (str): Button code ('A', 'B', 'C', or 'D')

        Example:
            async def my_callback(data):
                print(f"Received from {data['serial_number']:06X}: {data['button_code']}")

            protocol.register_rcv_callback(my_callback)
        """
        if callback not in self._rcv_callbacks:
            self._rcv_callbacks.append(callback)
            _LOGGER.debug("RCV callback registered, total: %d", len(self._rcv_callbacks))

    def unregister_rcv_callback(self, callback: Callable[[dict[str, Any]], None | object]) -> bool:
        """Unregister a previously registered RCV callback.

        Args:
            callback: The callback to remove

        Returns:
            True if callback was found and removed, False otherwise
        """
        try:
            self._rcv_callbacks.remove(callback)
            _LOGGER.debug("RCV callback unregistered, total: %d", len(self._rcv_callbacks))
            return True
        except ValueError:
            _LOGGER.warning("Callback not found in registered callbacks")
            return False

    def clear_rcv_callbacks(self) -> None:
        """Clear all registered RCV callbacks."""
        self._rcv_callbacks.clear()
        _LOGGER.debug("All RCV callbacks cleared")

    async def _wait_for_rcv_message(self) -> dict[str, Any] | None:
        """Wait until a RCV message is received via callback queue.

        This is used internally by receive_telegramm() to wait for messages.

        Returns:
            Dictionary with serial_number and button_code, or None on timeout
        """
        future: asyncio.Future[dict[str, Any]] = asyncio.Future()

        def temp_callback(data: dict[str, Any]) -> None:
            if not future.done():
                self.unregister_rcv_callback(temp_callback)
                future.set_result(data)

        self.register_rcv_callback(temp_callback)
        try:
            return await future
        except asyncio.CancelledError:
            self.unregister_rcv_callback(temp_callback)
            raise

    async def _invoke_rcv_callbacks(self, telegram_data: dict[str, Any]) -> None:
        """Invoke all registered RCV callbacks with telegram data.

        Args:
            telegram_data: Dictionary containing serial_number and button_code

        Called internally when a RCV message is received.
        """
        async with self._callback_lock:
            callbacks = list(self._rcv_callbacks)

        for callback in callbacks:
            try:
                _LOGGER.debug("Invoking RCV callback with data: %s", telegram_data)
                # Call callback and await if it's a coroutine
                result = callback(telegram_data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                _LOGGER.error("Error in RCV callback: %s", e)

    # ================================================================================================
    # INTERNAL ASYNC METHODS
    # ================================================================================================

    async def _send_and_receive(self, command: str, timeout: float = 5.0) -> str | None:
        """Send command and wait for response.

        Args:
            command: ASCII command
            timeout: Timeout in seconds

        Returns:
            Response string (without CR), or None on timeout/error
        """
        if not self._connected:
            raise RuntimeError("Not connected to RX09")

        async with self._lock:
            try:
                # Send command (would be via self._writer in real implementation)
                # self._writer.write((command + "\r").encode("ascii"))
                # await self._writer.drain()

                # Read response (with timeout)
                # response = await asyncio.wait_for(
                #     self._reader.readuntil(b"\r"), timeout=timeout
                # )
                # return response.decode("ascii").strip()

                # Placeholder: simulate response
                _LOGGER.debug("Command sent: %s", command)
                await asyncio.sleep(0.01)

                return "OK"  # Simulated response

            except asyncio.TimeoutError:
                _LOGGER.warning("Command timeout: %s", command)
                return None
            except Exception as e:
                _LOGGER.error("Send/receive error: %s", e)
                return None

    async def _reader_loop(self) -> None:
        """Background reader loop that listens for spontaneous RCV messages.

        This task runs continuously in the background and:
        1. Reads incoming messages from the device
        2. Distinguishes between RCV (spontaneous) and command responses
        3. Invokes registered callbacks for RCV messages

        RCV message format: REC,SERIAL_NUMBER,BUTTON_CODE
        where SERIAL_NUMBER is in hex (e.g., 123ABC) and BUTTON_CODE is A/B/C/D

        This is called internally when connect() is used with callback support.
        """
        _LOGGER.debug("Starting RCV message reader loop for port %s", self.port)

        while not self._shutdown_requested and self._connected:
            try:
                # Read a line from the device
                # In real implementation:
                # line = await asyncio.wait_for(
                #     self._reader.readuntil(b"\r"), timeout=1.0
                # )
                # message = line.decode("ascii", errors="ignore").strip()

                # For now, simulate by waiting
                await asyncio.sleep(1.0)
                message = ""  # Would be filled by actual read

                if not message:
                    continue

                _LOGGER.debug("Reader loop received message: %s", message)

                # Check if it's a spontaneous RCV message
                if message.startswith("REC"):
                    try:
                        parts = message.split(",")
                        if len(parts) >= 3:
                            # REC,SERIAL_NUMBER,BUTTON_CODE
                            serial_hex = parts[1]
                            button_code = parts[2].upper()

                            # Validate button code
                            if button_code not in ("A", "B", "C", "D"):
                                _LOGGER.warning("Invalid button code: %s", button_code)
                                continue

                            # Parse serial number (hex)
                            try:
                                serial_number = int(serial_hex, 16)
                            except ValueError:
                                _LOGGER.warning("Invalid serial number format: %s", serial_hex)
                                continue

                            telegram_data: dict[str, Any] = {
                                "serial_number": serial_number,
                                "serial_hex": serial_hex,
                                "button_code": button_code,
                            }

                            _LOGGER.info(
                                "Received RCV message: serial=%s button=%s",
                                serial_hex,
                                button_code,
                            )

                            # Invoke all registered callbacks
                            await self._invoke_rcv_callbacks(telegram_data)

                    except Exception as e:
                        _LOGGER.error("Error processing RCV message '%s': %s", message, e)

            except asyncio.CancelledError:
                _LOGGER.debug("Reader loop cancelled")
                break
            except Exception as e:
                _LOGGER.error("Reader loop error: %s", e)
                await asyncio.sleep(0.5)  # Backoff on error

        _LOGGER.debug("Reader loop stopped for port %s", self.port)

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
