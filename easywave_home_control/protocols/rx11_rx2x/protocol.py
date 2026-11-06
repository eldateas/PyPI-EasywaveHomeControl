"""Support for communicating with EASYWAVE RX11 transceivers.

This module implements the RxModule communication protocol used by
EASYWAVE RX11 devices, including packet encoding/decoding, version
queries, connection management, health checks, error tracking, and
callbacks for connection state changes.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import struct
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Any

from ...serial_io import SERIAL_ERRORS, async_serial_for_url

if TYPE_CHECKING:
    from ...serial_io import AsyncSerial

_LOGGER = logging.getLogger(__name__)

# Alias kept for internal use; includes SerialException, OSError, TimeoutError.
_SERIAL_ERRORS = SERIAL_ERRORS


# ====================================================================================================
# PROTOCOL CONSTANTS - SOP, EOP, Byte Stuffing
# ====================================================================================================

PREFIX = 0x80  # Prefix for byte stuffing
SOP = 0x81  # Start-of-packet
EOP = 0x82  # End-of-packet

STUFFING_MIN = 0x80  # Start of range which is stuffed
STUFFING_MAX = 0x82  # End of range which is stuffed
STUFFING_ADDEND = 0xFF & (-0x80)  # Addend to get the replacement (0x80)


# ====================================================================================================
# FUNCTION CODES
# ====================================================================================================


class FunctionCode(IntEnum):
    """Function codes for different IRP operations."""

    # Easywave Basic
    EW_RCV_BUTTON = 0x01
    EW_SEND_CMD = 0x02
    EW_RCV_EX = 0x03
    EW_GET_FD_SERIAL = 0x20

    # Easywave Bidi
    EWB_JOIN_DEVICE = 0x04
    EWB_REMOVE_DEVICE = 0x05
    EWB_CLEAR_NFILTER = 0x06
    EWB_ADD_NFILTER = 0x07
    EWB_RCV = 0x08
    EWB_CHANGE_STATE = 0x09
    EWB_QUERY_STATE = 0x0A
    EWB_TRLRN_CONTROL = 0x0B
    EWB_GET_FD_SERIAL = 0x21

    # Secwave Security
    SEC_RCV = 0xA1
    SEC_LEARN = 0xA2
    SEC_REPLY_QUERY = 0xA3
    SEC_DELETE = 0xA4
    SEC_STAT = 0xA5
    SEC_WR_USERDATA = 0xA6
    SEC_SEND_CMD_TEL = 0xA7
    SEC_SEND_LRN_TEL = 0xA8
    SEC_DELETE_ALL = 0xA9

    # Module Administration
    MA_QUERY_HW_VER = 0xC0
    MA_QUERY_FW_VER = 0xC1
    MA_UPDATE_FW = 0xC2

    # Control
    CANCEL_IO = 0xFE
    CANCEL_ALL_IO = 0xFF
    PING_RCV = 0xF0


# Shortcuts for FunctionCode enum values
EW_RCV_BUTTON = FunctionCode.EW_RCV_BUTTON
EW_SEND_CMD = FunctionCode.EW_SEND_CMD
MA_QUERY_HW_VER = FunctionCode.MA_QUERY_HW_VER
MA_QUERY_FW_VER = FunctionCode.MA_QUERY_FW_VER
CANCEL_IO = FunctionCode.CANCEL_IO
CANCEL_ALL_IO = FunctionCode.CANCEL_ALL_IO
PING_RCV = FunctionCode.PING_RCV

# Continuous receive function codes - these wait indefinitely for incoming telegrams
# and should not be considered "stuck" in health checks
CONTINUOUS_RCV_FUNCTIONS: frozenset[int] = frozenset(
    {
        FunctionCode.EW_RCV_BUTTON,
        FunctionCode.EW_RCV_EX,
        FunctionCode.EWB_RCV,
        FunctionCode.SEC_RCV,
    }
)


# ====================================================================================================
# ERROR CODES
# ====================================================================================================


class ErrorCode(IntEnum):
    """Error codes returned by operations."""

    SUCCESS = 0x00
    ERR_CANCELED = 0x01
    ERR_OUT_OF_QUEUE = 0x02
    ERR_INVALID_REQUEST = 0x03
    ERR_SIZE_MISMATCH = 0x04
    ERR_INVALID_PARAMETER = 0x05
    ERR_INCOMPLETE_FW = 0x06
    ERR_RF_TIMEOUT = 0x07
    ERR_INVALID_SERIAL = 0x08
    ERR_SUPERSEDED = 0x09
    ERR_INCOMPAT_FW = 0x0A
    ERR_SERIAL_FILTER = 0x0B
    ERR_FILTER_OUT_OF_MEM = 0x0C
    ERR_INVALID_SEC_REPLY = 0x0D
    ERR_TOO_LATE = 0x0E
    ERR_FAILSTATE = 0xFF


# ====================================================================================================
# INFO TYPES
# ====================================================================================================


class InfoType(IntEnum):
    """Info types for received telegrams."""

    TM_IT_EASW_RELEASE = 0x00  # Easywave transmitter; button release
    TM_IT_EASW_PUSH = 0x01  # Easywave transmitter; button push and hold
    TM_IT_SENSOR_DATA = 0x02  # Sensor data message
    TM_IT_EWBIDI_STATE = 0x03  # Easywave Bidi receiver state change
    TM_IT_EWBIDI_ABORT = 0x40  # Easywave Bidi notification about abort
    TM_IT_EWBIDI_ADD_TR = 0x41  # Easywave Bidi notification about learned transmitter
    TM_IT_EWBIDI_RMV_TR = 0x42  # Easywave Bidi notification about removed transmitter
    TM_IT_EWBIDI_LN_T = 0xF0  # Easywave Bidi learn ack for transmitter
    TM_IT_EWBIDI_CHG_T = 0xF1  # Easywave Bidi receiver change state for transmitters
    TM_IT_EWBIDI_QUR_T = 0xF2  # Easywave Bidi receiver query state for transmitters


# ====================================================================================================
# DEVICE TYPES
# ====================================================================================================


class DeviceType(IntEnum):
    """Device types for EWB devices."""

    EMPTY_TYPE = 0x00
    EWB_DT_BIDI_TR = 0x01  # Generic Easywave Bidi transmitter
    EWB_DT_SWITCH = 0x03  # Switch (on/off)
    EWB_DT_DIMMER = 0x04  # Dimmer
    EWB_DT_MOTOR = 0x05  # Motor control
    EWB_DT_DUAL_SWITCH = 0x06  # Dual switch (on/off)
    EWB_DT_QUAD_SWITCH = 0x07  # Quadruple switch (on/off)
    EWB_DT_DUAL_MOTOR = 0x08  # Dual motor control
    EWB_DT_QUAD_MOTOR = 0x09  # Quadruple motor control


# ====================================================================================================
# BUTTON CONSTANTS
# ====================================================================================================

TM_BUTTON_MASK = 0x03
TM_BUTTON_A = 0
TM_BUTTON_B = 1
TM_BUTTON_C = 2
TM_BUTTON_D = 3

TM_BUTTON_FUNC_MASK = 0xFC
TM_BUTTON_DEFAULT = 0x00
TM_BUTTON_LRN_DEL = 0x04
TM_BUTTON_LRN_ADD = 0x08
TM_BUTTON_LRN_RESET = 0x0C
TM_BUTTON_LRN_TIMER = 0x10
TM_BUTTON_HOLD = 0x14
TM_BUTTON_RELEASE = 0x18
TM_BUTTON_LOWBAT = 0x80


# ====================================================================================================
# REQUEST & COMPLETION STRUCTURES
# ====================================================================================================


@dataclass
class IRP:
    """I/O Request Packet - represents a command to be sent."""

    function: int
    params: bytes = field(default_factory=bytes)


@dataclass
class ICP:
    """I/O Completion Packet - represents a response received."""

    handle: int = 0
    result: int = ErrorCode.ERR_FAILSTATE
    data: bytes = field(default_factory=bytes)


@dataclass
class Request:
    """Represents a pending request with its IRP and expected ICP."""

    irp: IRP
    irp_byte_count: int
    expected_icp_byte_count: int
    req_str: str

    # State tracking
    completed: bool = False
    queued: bool = False
    cancel: bool = False
    handle: int = 0
    is_continuous: bool = False
    error: str | None = None
    done: bool = False

    # Result
    icp: ICP = field(default_factory=ICP)

    async def wait(self, timeout: float | None = None) -> bool:
        """Wait for request completion with async polling."""
        start_time = time.time()
        poll_interval = 0.001  # 1ms polling interval

        while not self.completed:
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    return False
            await asyncio.sleep(poll_interval)

        return True

    def signal(self) -> None:
        """Signal request completion."""
        self.completed = True


# ====================================================================================================
# BYTE STUFFING FUNCTIONS
# ====================================================================================================


def apply_byte_stuffing(data: bytes) -> bytes:
    """Apply byte stuffing to data bytes."""
    result = bytearray()
    for byte in data:
        if STUFFING_MIN <= byte <= STUFFING_MAX:
            result.append(PREFIX)
            result.append((byte + STUFFING_ADDEND) & 0xFF)
        else:
            result.append(byte)
    return bytes(result)


def remove_byte_stuffing(data: bytes) -> tuple[bytes, bool]:
    """Remove byte stuffing from data."""
    result = bytearray()
    i = 0
    while i < len(data):
        byte = data[i]
        if byte == PREFIX:
            if i + 1 >= len(data):
                return bytes(result), False
            next_byte = data[i + 1]
            if (
                ((STUFFING_MIN + STUFFING_ADDEND) & 0xFF)
                <= next_byte
                <= ((STUFFING_MAX + STUFFING_ADDEND) & 0xFF)
            ):
                result.append((next_byte + STUFFING_ADDEND) & 0xFF)
                i += 2
            else:
                return bytes(result), False
        else:
            result.append(byte)
            i += 1
    return bytes(result), True


# ====================================================================================================
# PACKET ENCODING/DECODING
# ====================================================================================================


def encode_irp(irp: IRP) -> bytes:
    """Encode an IRP into a byte packet with SOP, function, params, stuffing, and EOP."""
    buffer = bytearray([irp.function])
    buffer.extend(irp.params)
    stuffed = apply_byte_stuffing(bytes(buffer))
    packet = bytearray([SOP])
    packet.extend(stuffed)
    packet.append(EOP)
    return bytes(packet)


def decode_packet(raw_buffer: bytes) -> tuple[ICP | None, int, bool]:
    """Decode a received packet into an ICP.

    Note: raw_buffer is already unstuffed by _process_received_byte()!
    It still contains SOP and EOP markers but byte stuffing has been removed.

    Returns:
        (icp, function_code, success)
    """
    # Remove SOP and EOP
    if len(raw_buffer) < 2 or raw_buffer[0] != SOP or raw_buffer[-1] != EOP:
        return None, 0, False

    # Payload is already unstuffed - no need to call remove_byte_stuffing()!
    payload = raw_buffer[1:-1]

    if len(payload) < 2:
        return None, 0, False

    # Parse handle (first 2 bytes)
    handle = (payload[0] << 8) | payload[1]

    # Check if this is just an IPP (handle only) or a full ICP
    if len(payload) == 2:
        # IPP - just a handle
        icp = ICP(handle=handle, result=ErrorCode.SUCCESS, data=b"")
        return icp, 0, True

    # Full ICP - handle + result + data
    result = payload[2]
    data = payload[3:] if len(payload) > 3 else b""

    icp = ICP(handle=handle, result=result, data=data)
    return icp, 0, True


# ====================================================================================================
# IRP PARAMETER ENCODING
# ====================================================================================================


def encode_uint16(value: int) -> bytes:
    """Encode a uint16 as big-endian bytes."""
    return struct.pack(">H", value)


def encode_uint32(value: int) -> bytes:
    """Encode a uint32 as big-endian bytes."""
    return struct.pack(">I", value)


def encode_serial_array(serial_bytes: bytes) -> bytes:
    """Encode a 16-byte serial number."""
    if len(serial_bytes) != 16:
        raise ValueError(f"Serial must be 16 bytes, got {len(serial_bytes)}")
    return serial_bytes


# ====================================================================================================
# ICP DATA PARSING
# ====================================================================================================


def parse_icp_data(icp: ICP, function: int) -> dict[str, Any]:
    """Parse ICP data based on the function code."""
    data = icp.data
    result: dict[str, Any] = {}

    if icp.result != ErrorCode.SUCCESS:
        return result

    offset = 0

    try:
        if function == FunctionCode.EWB_JOIN_DEVICE:
            result["receiver"] = data[offset : offset + 16]
            offset += 16
            result["device_type"] = data[offset]

        elif function in (
            FunctionCode.EW_RCV_BUTTON,
            FunctionCode.EW_RCV_EX,
            FunctionCode.EWB_RCV,
        ):
            result["info_type"] = data[offset]
            offset += 1
            result["receiver_or_transmitter"] = data[offset : offset + 16]
            offset += 16

            # Parse InfoData based on InfoType
            info_type = result["info_type"]
            if info_type == InfoType.TM_IT_EASW_PUSH:
                result["info_data"] = data[offset : offset + 1]
            elif info_type == InfoType.TM_IT_SENSOR_DATA:
                result["info_data"] = data[offset : offset + 8]
            elif info_type == InfoType.TM_IT_EWBIDI_STATE:
                result["info_data"] = data[offset : offset + 5]
            else:
                result["info_data"] = bytes(8)  # Zeroed

        elif function in (
            FunctionCode.EWB_CHANGE_STATE,
            FunctionCode.EWB_QUERY_STATE,
            FunctionCode.EWB_TRLRN_CONTROL,
        ):
            result["mode"] = data[offset]
            offset += 1
            result["state"] = data[offset : offset + 4]

        elif function in (FunctionCode.EW_GET_FD_SERIAL, FunctionCode.EWB_GET_FD_SERIAL):
            result["gateway"] = data[offset : offset + 16]

        elif function in (FunctionCode.SEC_RCV, FunctionCode.SEC_LEARN):
            result["stor_index"] = struct.unpack(">H", data[offset : offset + 2])[0]
            offset += 2
            result["sec_query"] = data[offset]
            offset += 1
            result["sec_cmd"] = struct.unpack(">H", data[offset : offset + 2])[0]
            offset += 2
            result["user_data"] = struct.unpack(">I", data[offset : offset + 4])[0]
            offset += 4
            result["sec_flags"] = data[offset]
            offset += 1
            result["lrn_tel"] = data[offset]

        elif function in (FunctionCode.SEC_DELETE, FunctionCode.SEC_STAT):
            result["is_used"] = data[offset] != 0
            offset += 1
            result["user_data"] = struct.unpack(">I", data[offset : offset + 4])[0]

        elif function in (
            FunctionCode.SEC_SEND_CMD_TEL,
            FunctionCode.SEC_SEND_LRN_TEL,
        ):
            if len(data) >= offset + 4:
                result["primary_state"] = struct.unpack(">H", data[offset : offset + 2])[0]
                offset += 2
                result["secondary_state"] = struct.unpack(">H", data[offset : offset + 2])[0]

        elif function == FunctionCode.MA_QUERY_HW_VER:
            result["hw_version_str"] = data[offset : offset + 16]

        elif function == FunctionCode.MA_QUERY_FW_VER:
            result["major_version"] = data[offset]
            offset += 1
            result["minor_version"] = data[offset]
            offset += 1
            result["incomplete_fw"] = data[offset] != 0 if offset < len(data) else False

        elif function == FunctionCode.MA_UPDATE_FW:
            result["is_restarting"] = data[offset] != 0

    except (IndexError, struct.error) as e:
        _LOGGER.error("Error parsing ICP data for function 0x%02x: %s", function, e)

    return result


# ====================================================================================================
# MAIN RX MODULE CLASS
# ====================================================================================================


class RxModule:
    """Pure Python implementation of EASYWAVE RX11 RxModule - Core Version.

    This is a minimal but complete implementation focused on:
    - Hardware/firmware version queries
    - Button telegram receiving
    - Health monitoring
    - Graceful disconnect
    - COM port compatibility (no direct USB calls)
    """

    MAX_REQUEST_COUNT = 8
    MAX_REQUEST_QUEUED = 12

    def __init__(self, port: str, baudrate: int = 115200) -> None:
        """Initialize the RxModule."""
        self.port = port
        self.baudrate = baudrate

        # Serial connection (serialx AsyncSerial — never blocks the event loop)
        self._serial: AsyncSerial | None = None
        self._connected = False
        self._shutdown_requested = False
        self._is_reconnecting = False

        # Outbound IRP packets drained by ``_serial_handler`` via await write()
        self._write_queue: deque[bytes] = deque()
        self._write_wakeup: asyncio.Event | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

        # Request queues
        self._tx_req_queued: list[Request | None] = [None] * self.MAX_REQUEST_QUEUED
        self._tx_req_queued_front = -1
        self._tx_req_queued_rear = -1
        self._tx_req_queued_size = 0

        self._tx_req_sent: list[Request | None] = [None] * self.MAX_REQUEST_COUNT
        self._tx_req_sent_front = -1
        self._tx_req_sent_rear = -1
        self._tx_req_sent_size = 0

        self._req_pending: dict[int, Request] = {}

        # State tracking
        self._state_good = True
        self._connection_healthy = True
        self._hardware_error = False
        self._last_error: str | None = None
        self._last_successful_communication = time.time()
        self._reconnect_attempts = 0
        self._reconnect_delay_base = 1.0

        # Startup tolerance - ignore decode errors on initial connection
        self._startup_tolerance_until: float = 0.0
        self._startup_tolerance_duration: float = 5.0
        self._reconnect_startup_tolerance_duration: float = 10.0

        # Cancel tolerance - allow unknown handle ICPs after cancel_all_io
        self._cancel_tolerance_until: float = 0.0

        # RX state
        self._rx_sop = False
        self._rx_raw_buffer = bytearray()
        self._rx_stuffing = False

        # Threading & Async
        self._protocol_lock = threading.RLock()
        self._file_lock = threading.Lock()
        self._serial_handler_ready = asyncio.Event()
        self._serial_handler_task: asyncio.Task[None] | None = None  # Set during connect()

        # Send command loop (for dead man's switch)
        self._send_cmd_loop_task: asyncio.Task[None] | None = None
        self._send_cmd_loop_running = False
        self._send_cmd_loop_gateway: bytes | None = None
        self._send_cmd_loop_button: int | None = None

        # Send command loop pipelining
        self._send_cmd_loop_lock = threading.Lock()  # Protect pipeline state
        self._send_cmd_loop_queue: list[Request] = []  # Prepared requests ready to send
        self._send_cmd_loop_pending: list[Request] = []  # Requests waiting for completion
        self._send_cmd_loop_drain = False  # Signal to drain remaining requests on stop

        # Send command loop statistics & error tracking
        self._send_cmd_loop_stats: dict[str, Any] = {
            "sent": 0,  # Total commands sent
            "success": 0,  # Successful completions
            "errors": 0,  # Failed commands
            "last_error": None,  # Last error encountered
            "last_error_time": None,  # When last error occurred
        }
        self._send_cmd_loop_consecutive_errors = 0  # Count of consecutive errors
        self._send_cmd_loop_backoff_delay = 0.1  # Base backoff in seconds
        self._send_cmd_loop_max_backoff = 5.0  # Max backoff in seconds

        # Callbacks
        self._disconnect_callback: Callable[[], None] | None = None
        self._reconnect_callback: Callable[[], None] | None = None

    # ================================================================================================
    # PROPERTIES
    # ================================================================================================

    def set_disconnect_callback(self, callback: Callable[[], None] | None) -> None:
        """Set a callback to be called when a disconnect/hardware error occurs."""
        self._disconnect_callback = callback

    def set_reconnect_callback(self, callback: Callable[[], None] | None) -> None:
        """Set a callback to be called after a successful reconnect."""
        self._reconnect_callback = callback

    def _notify_disconnect(self) -> None:
        """Notify the disconnect callback if registered.

        Supports both sync and async callbacks. If async, schedules as task.
        """
        if self._disconnect_callback is None:
            return

        try:
            result = self._disconnect_callback()
            # If callback is async (returns coroutine), schedule it
            if hasattr(result, '__await__'):
                try:
                    asyncio.create_task(result)  # type: ignore[arg-type]
                except RuntimeError:
                    # No event loop running - can't schedule async callback
                    _LOGGER.debug("Cannot schedule async disconnect callback without event loop")
        except (OSError, RuntimeError) as e:
            _LOGGER.warning("Error in disconnect callback: %s", e)

    def _notify_reconnect(self) -> None:
        """Notify the reconnect callback if registered.

        Supports both sync and async callbacks. If async, schedules as task.
        """
        if self._reconnect_callback is None:
            return

        try:
            result = self._reconnect_callback()
            # If callback is async (returns coroutine), schedule it
            if hasattr(result, '__await__'):
                try:
                    asyncio.create_task(result)  # type: ignore[arg-type]
                except RuntimeError:
                    # No event loop running - can't schedule async callback
                    _LOGGER.debug("Cannot schedule async reconnect callback without event loop")
        except (OSError, RuntimeError) as e:
            _LOGGER.warning("Error in reconnect callback: %s", e)

    def _transition_to_error(self) -> bool:
        """Atomically transition to hardware error state.

        Sets _connected, _state_good, _connection_healthy, _hardware_error.

        Returns:
            True if this is a NEW disconnect (was previously connected), so the
            caller knows whether to fire the disconnect callback exactly once.
        """
        with self._protocol_lock:
            was_connected = self._connected
            self._state_good = False
            self._connection_healthy = False
            self._hardware_error = True
            self._connected = False
        return bool(was_connected)

    @property
    def is_connected(self) -> bool:
        """Check if module is connected and healthy."""
        with self._protocol_lock:
            return self._connected and self._connection_healthy and self._state_good

    @property
    def state_good(self) -> bool:
        """Check if module state is good (no protocol errors)."""
        with self._protocol_lock:
            return self._state_good

    @property
    def connection_status(self) -> str:
        """Get detailed connection status."""
        with self._protocol_lock:
            if self._hardware_error:
                return "hardware_error"
            if not self._connected:
                return "disconnected"
            if not self._connection_healthy:
                return "reconnecting"
            if not self._state_good:
                return "error"
            return "connected"

    @property
    def has_hardware_error(self) -> bool:
        """Check if a hardware error occurred (USB disconnected, I/O error, etc.)."""
        with self._protocol_lock:
            return self._hardware_error

    @property
    def last_error(self) -> str | None:
        """Get the last error message."""
        with self._protocol_lock:
            return self._last_error

    # ================================================================================================
    # CONNECTION MANAGEMENT
    # ================================================================================================

    async def connect(self) -> bool:
        """Connect to the RX11 module (async serialx — no loop blocking)."""
        try:
            self._shutdown_requested = False
            self._loop = asyncio.get_running_loop()
            self._write_queue.clear()
            self._write_wakeup = asyncio.Event()

            # Open serial connection asynchronously (serialx)
            serial_port = async_serial_for_url(
                self.port,
                baudrate=self.baudrate,
                byte_size=8,
                parity="N",
                stopbits=1,
                exclusive=True,
            )
            await serial_port.open()
            self._serial = serial_port

            # Drain stale bytes BEFORE starting the RX handler (single reader)
            drained = await self._drain_input(duration=0.4)
            if drained > 0:
                _LOGGER.debug("Drained %d stale bytes from serial buffer", drained)

            # Start serial handler before any protocol communication
            self._serial_handler_ready = asyncio.Event()
            self._serial_handler_task = asyncio.create_task(
                self._serial_handler(),
                name=f"rxmodule-serial-{self.port}",
            )
            try:
                await asyncio.wait_for(self._serial_handler_ready.wait(), timeout=1.0)
            except TimeoutError:
                _LOGGER.error("Serial handler failed to start within 1s")
                await self.dispose()
                return False

            # Reset state
            self._reset_queues()
            await self.cancel_all_io_requests()
            self._reset_rx_state()

            # Set startup tolerance
            tolerance_duration = (
                self._reconnect_startup_tolerance_duration
                if self._is_reconnecting
                else self._startup_tolerance_duration
            )
            self._startup_tolerance_until = time.time() + tolerance_duration

            # Reset health state
            with self._protocol_lock:
                self._state_good = True
                self._connection_healthy = True
                self._hardware_error = False
                self._last_error = None
                self._last_successful_communication = time.time()
                self._reconnect_attempts = 0

            self._connected = True
        except _SERIAL_ERRORS:
            await self._cleanup_failed_connect()
            return False
        else:
            return True

    async def _cleanup_failed_connect(self) -> None:
        """Best-effort cleanup after a failed connect()."""
        self._shutdown_requested = True
        if self._write_wakeup is not None:
            self._write_wakeup.set()
        if self._serial_handler_task and not self._serial_handler_task.done():
            self._serial_handler_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, TimeoutError):
                await asyncio.wait([self._serial_handler_task], timeout=1.0)
        if self._serial is not None:
            with contextlib.suppress(*_SERIAL_ERRORS):
                await self._serial.close()
            self._serial = None
        self._serial_handler_task = None
        self._connected = False

    async def _drain_input(self, *, duration: float) -> int:
        """Discard inbound bytes for ``duration`` seconds using async reads."""
        if not self._serial or not self._serial.is_open:
            return 0
        drained = 0
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                chunk = await asyncio.wait_for(
                    self._serial.read(256),
                    timeout=min(0.05, remaining),
                )
            except TimeoutError:
                continue
            except _SERIAL_ERRORS:
                break
            if not chunk:
                break
            drained += len(chunk)
        return drained

    async def flush_serial_buffer(self) -> None:
        """Reset RX parser state.

        Stale-byte draining happens at connect time (before the handler starts).
        Concurrent ``read()`` against the running handler is not safe with
        serialx AsyncSerial, so runtime flush only clears framing state.
        """
        self._reset_rx_state()

    async def dispose(self) -> None:
        """Disconnect and cleanup."""
        self._shutdown_requested = True
        if self._write_wakeup is not None:
            self._write_wakeup.set()
        await self.cancel_all_io_requests()

        # Wait for serial handler task
        if self._serial_handler_task and not self._serial_handler_task.done():
            try:
                await asyncio.wait([self._serial_handler_task], timeout=3.0)
            except (TimeoutError, AttributeError):
                pass
            if not self._serial_handler_task.done():
                self._serial_handler_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._serial_handler_task

        # Drain remaining bytes then close
        if self._serial and self._serial.is_open:
            with contextlib.suppress(*_SERIAL_ERRORS):
                await self._drain_input(duration=0.2)

        if self._serial is not None:
            try:
                await self._serial.close()
            except _SERIAL_ERRORS as e:
                _LOGGER.debug("Error closing serial connection: %s", e)
            finally:
                self._serial = None

        self._serial_handler_task = None
        self._write_queue.clear()
        self._write_wakeup = None
        self._connected = False

    def _reset_queues(self):
        """Reset all request queues."""
        self._tx_req_queued = [None] * self.MAX_REQUEST_QUEUED
        self._tx_req_queued_front = -1
        self._tx_req_queued_rear = -1
        self._tx_req_queued_size = 0

        self._tx_req_sent = [None] * self.MAX_REQUEST_COUNT
        self._tx_req_sent_front = -1
        self._tx_req_sent_rear = -1
        self._tx_req_sent_size = 0

        self._req_pending.clear()

    def _reset_rx_state(self):
        """Reset RX state machine."""
        self._rx_sop = False
        self._rx_raw_buffer = bytearray()
        self._rx_stuffing = False

    # ================================================================================================
    # REQUEST MANAGEMENT
    # ================================================================================================

    def _create_request(
        self, irp: IRP, irp_byte_count: int, expected_icp_byte_count: int, req_str: str
    ) -> Request:
        """Create a new request."""
        return Request(
            irp=irp,
            irp_byte_count=irp_byte_count,
            expected_icp_byte_count=expected_icp_byte_count,
            req_str=req_str,
            is_continuous=irp.function in CONTINUOUS_RCV_FUNCTIONS,
        )

    def _place_request(self, req: Request):
        """Place a request in the queue or send it immediately."""
        with self._protocol_lock:
            if not self._state_good:
                req.icp = ICP(handle=0, result=ErrorCode.ERR_FAILSTATE)
                req.signal()
                return

            if (
                self._tx_req_queued_size == 0
                and (self._tx_req_sent_size + len(self._req_pending)) < self.MAX_REQUEST_COUNT
            ):
                self._enqueue_sent(req)
                self._write_to_buffer(req.irp, req.req_str)
            elif self._tx_req_queued_size < self.MAX_REQUEST_QUEUED:
                self._remove_canceled_queued_requests()
                self._enqueue_queued(req)
                req.queued = True
            else:
                req.icp = ICP(handle=0, result=ErrorCode.ERR_OUT_OF_QUEUE)
                req.signal()

    def _enqueue_queued(self, req: Request):
        """Add request to queued list."""
        if self._tx_req_queued_front == -1:
            self._tx_req_queued_front = 0
        self._tx_req_queued_rear = (self._tx_req_queued_rear + 1) % self.MAX_REQUEST_QUEUED
        self._tx_req_queued[self._tx_req_queued_rear] = req
        self._tx_req_queued_size += 1

    def _dequeue_queued(self) -> Request | None:
        """Remove request from queued list."""
        if self._tx_req_queued_size == 0:
            return None
        req = self._tx_req_queued[self._tx_req_queued_front]
        self._tx_req_queued[self._tx_req_queued_front] = None
        self._tx_req_queued_front = (self._tx_req_queued_front + 1) % self.MAX_REQUEST_QUEUED
        self._tx_req_queued_size -= 1
        return req

    def _enqueue_sent(self, req: Request):
        """Add request to sent list."""
        if self._tx_req_sent_front == -1:
            self._tx_req_sent_front = 0
        self._tx_req_sent_rear = (self._tx_req_sent_rear + 1) % self.MAX_REQUEST_COUNT
        self._tx_req_sent[self._tx_req_sent_rear] = req
        self._tx_req_sent_size += 1

    def _dequeue_sent(self) -> Request | None:
        """Remove request from sent list."""
        if self._tx_req_sent_size == 0:
            return None
        req = self._tx_req_sent[self._tx_req_sent_front]
        self._tx_req_sent[self._tx_req_sent_front] = None
        self._tx_req_sent_front = (self._tx_req_sent_front + 1) % self.MAX_REQUEST_COUNT
        self._tx_req_sent_size -= 1
        return req

    def _remove_canceled_queued_requests(self):
        """Remove canceled requests from the queued list."""
        while self._tx_req_queued_size > 0:
            req = self._tx_req_queued[self._tx_req_queued_front]
            if req and req.cancel:
                self._dequeue_queued()
            else:
                break

    async def _wait_for_request(self, req: Request, timeout: float | None) -> bool:
        """Wait for a request with proper timeout and cleanup.

        Args:
            req: Request to wait for
            timeout: Timeout in seconds, or None for indefinite waiting

        Returns:
            True if request completed, False if timeout occurred
        """
        try:
            completed = await req.wait(timeout)
        except asyncio.CancelledError:
            self._release_outstanding_request(
                req,
                result=ErrorCode.ERR_CANCELED,
                reason="cancelled",
            )
            raise

        if not completed:
            waited = timeout if timeout is not None else -1
            self._release_outstanding_request(
                req,
                result=ErrorCode.ERR_RF_TIMEOUT,
                reason=f"timed out ({waited:.1f}s)",
            )

        return completed

    def _release_outstanding_request(self, req: Request, *, result: int, reason: str) -> None:
        """Drop a request the caller is no longer waiting for.

        A receive such as ``EW_RCV_EX`` stays in ``_req_pending`` until a telegram
        arrives. Queued requests are discarded. A request that already has a
        module handle is cancelled on the device. A request still waiting for
        its IPP stays in the sent list with ``cancel`` set, so the IPP path
        sends ``CANCEL_IO`` once the handle is known.
        """
        if req.completed:
            return

        _LOGGER.warning("Request '%s' %s - removing from queue", req.req_str, reason)
        req.cancel = True
        req.icp = ICP(handle=req.handle, result=result)
        req.signal()

        with self._protocol_lock:
            if self._drop_queued_request(req):
                return
            # No handle yet: keep the sent entry so the IPP path sends CANCEL_IO.
            if self._sent_request_is(req):
                return
            if req.handle and self._req_pending.get(req.handle) is req:
                del self._req_pending[req.handle]
                self._cancel_request_impl(req)
                self._cancel_tolerance_until = time.time() + 2.0

    def _drop_queued_request(self, req: Request) -> bool:
        """Remove ``req`` from the not-yet-sent queue. Caller holds ``_protocol_lock``."""
        if self._tx_req_queued_size == 0:
            return False
        kept: list[Request] = []
        found = False
        while self._tx_req_queued_size > 0:
            item = self._dequeue_queued()
            if item is req:
                found = True
                continue
            if item is not None:
                kept.append(item)
        for item in kept:
            self._enqueue_queued(item)
        return found

    def _sent_request_is(self, req: Request) -> bool:
        """Return whether ``req`` is still waiting for an IPP. Caller holds the lock."""
        if self._tx_req_sent_size == 0:
            return False
        front = self._tx_req_sent_front
        for offset in range(self._tx_req_sent_size):
            idx = (front + offset) % self.MAX_REQUEST_COUNT
            if self._tx_req_sent[idx] is req:
                return True
        return False

    # ================================================================================================
    # SERIAL COMMUNICATION
    # ================================================================================================

    def _write_to_buffer(self, irp: IRP, req_str: str) -> None:
        """Enqueue an IRP for async write by ``_serial_handler``.

        Never touches the serial port from the caller — writes are drained
        exclusively via ``await serial.write(...)`` on the event loop.
        """
        if self._shutdown_requested:
            return

        packet = encode_irp(irp)
        with self._file_lock:
            self._write_queue.append(packet)
        if self._write_wakeup is not None:
            self._write_wakeup.set()

    async def _flush_writes(self) -> bool:
        """Drain the outbound write queue. Returns False on I/O failure."""
        while True:
            with self._file_lock:
                if not self._write_queue:
                    return True
                packet = self._write_queue.popleft()

            if not self._serial or self._shutdown_requested:
                return False

            try:
                if not self._serial.is_open:
                    _LOGGER.error("Serial port no longer valid (USB disconnected?)")
                    if self._transition_to_error():
                        self._notify_disconnect()
                    return False
                await self._serial.write(packet)
            except _SERIAL_ERRORS as e:
                if not self._shutdown_requested:
                    _LOGGER.error("Serial error during write: %s", e)
                    if self._transition_to_error():
                        self._notify_disconnect()
                return False

    def _is_serial_port_valid(self) -> bool:
        """Check if the async serial port is still open."""
        try:
            return bool(self._serial and self._serial.is_open)
        except (OSError, ValueError, AttributeError) as e:
            _LOGGER.warning("Error checking serial port validity: %s", e)
            return False

    async def _serial_handler(self) -> None:
        """Async serial RX/TX loop — no blocking pyserial calls on the loop."""
        assert self._write_wakeup is not None
        self._serial_handler_ready.set()
        read_task: asyncio.Task[bytes] | None = None

        try:
            while not self._shutdown_requested:
                if not self._is_serial_port_valid():
                    if not self._shutdown_requested:
                        _LOGGER.error(
                            "Serial port invalid - USB device may have been removed"
                        )
                        if self._transition_to_error():
                            self._notify_disconnect()
                    break

                # Drain outbound IRPs, then promote queued requests → more writes
                if not await self._flush_writes():
                    break
                self._process_queued_requests()
                if not await self._flush_writes():
                    break

                if self._serial is None:
                    break

                if read_task is None:
                    read_task = asyncio.create_task(
                        self._serial.read(256),
                        name="rxmodule-serial-read",
                    )

                self._write_wakeup.clear()
                wake_task = asyncio.create_task(self._write_wakeup.wait())
                done, _pending = await asyncio.wait(
                    {read_task, wake_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if wake_task not in done:
                    wake_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await wake_task

                if read_task in done:
                    try:
                        data = read_task.result()
                    except asyncio.CancelledError:
                        raise
                    except _SERIAL_ERRORS as e:
                        if not self._shutdown_requested:
                            _LOGGER.warning("Serial handler read error: %s", e)
                            if self._transition_to_error():
                                self._notify_disconnect()
                        break
                    finally:
                        read_task = None

                    if not data:
                        if not self._shutdown_requested:
                            _LOGGER.error(
                                "Serial EOF - USB device may have been removed"
                            )
                            if self._transition_to_error():
                                self._notify_disconnect()
                        break

                    for byte in data:
                        self._process_received_byte(byte)
                # else: wake-only — keep ``read_task`` for the next wait cycle

        except asyncio.CancelledError:
            raise
        except _SERIAL_ERRORS as e:
            if not self._shutdown_requested:
                _LOGGER.warning("Serial handler error: %s", e)
                if self._transition_to_error():
                    self._notify_disconnect()
        finally:
            if read_task is not None and not read_task.done():
                read_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await read_task

    def _process_received_byte(self, byte: int):
        """Process a single received byte."""
        if not self._state_good:
            return

        # Handle start-of-packet before buffering to avoid accumulating
        # stray bytes when not synchronized.
        if byte == SOP:
            if self._rx_sop:
                _LOGGER.warning(
                    "Unexpected SOP while already in packet (len=%d)",
                    len(self._rx_raw_buffer),
                )
            # Always resynchronize buffer on SOP to discard any stray bytes
            self._rx_raw_buffer = bytearray([SOP])
            self._rx_sop = True
            self._rx_stuffing = False
            return

        # If we have not yet seen SOP, ignore bytes and ensure the buffer
        # does not grow without bound.
        if not self._rx_sop:
            self._rx_raw_buffer = bytearray()
            return

        # From here on, we are inside a packet: buffer the byte.
        self._rx_raw_buffer.append(byte)

        if byte == EOP:
            if self._rx_stuffing:
                _LOGGER.warning("Unexpected EOP while waiting for stuffed byte")
                self._reset_rx_state()
                return

            self._process_complete_packet()
            return

        if not self._rx_stuffing and byte == PREFIX:
            self._rx_stuffing = True
            self._rx_raw_buffer.pop()
            return

        if self._rx_stuffing:
            if (
                ((STUFFING_MIN + STUFFING_ADDEND) & 0xFF)
                <= byte
                <= ((STUFFING_MAX + STUFFING_ADDEND) & 0xFF)
            ):
                unstuffed = (byte + STUFFING_ADDEND) & 0xFF
                self._rx_raw_buffer[-1] = unstuffed
                self._rx_stuffing = False
            else:
                _LOGGER.warning("Invalid stuffed byte 0x%02x", byte)
                self._rx_raw_buffer = bytearray()
                self._rx_sop = False
                self._rx_stuffing = False
                return

        if len(self._rx_raw_buffer) >= 128:
            _LOGGER.warning("Packet too large (>128 bytes)")
            self._reset_rx_state()

    def _process_complete_packet(self):
        """Process a complete received packet."""
        raw_buffer = bytes(self._rx_raw_buffer)
        self._rx_raw_buffer = bytearray()
        self._rx_sop = False

        icp, _, success = decode_packet(raw_buffer)
        if not success or icp is None:
            in_startup = time.time() < self._startup_tolerance_until
            if in_startup:
                _LOGGER.debug("Discarding invalid packet during startup (len=%d)", len(raw_buffer))
            elif len(raw_buffer) > 0:
                _LOGGER.warning(
                    "Failed to decode packet (len=%d, hex=%s)",
                    len(raw_buffer),
                    raw_buffer.hex()[:80],
                )

            # If we have sent requests waiting and we're outside startup,
            # fail the oldest to recover sync
            if not in_startup:
                with self._protocol_lock:
                    if self._tx_req_sent_size > 0 and len(self._req_pending) == 0:
                        _LOGGER.error(
                            "Corrupt packet with pending requests — failing oldest sent request to recover sync"
                        )
                        req = self._dequeue_sent()
                        if req:
                            req.icp = ICP(handle=0, result=ErrorCode.ERR_FAILSTATE)
                            req.signal()
            return

        self._mark_communication_success()

        icp_byte_count = len(raw_buffer) - 2
        handle = icp.handle

        if icp_byte_count == 2:
            self._process_ipp(handle, raw_buffer)
        else:
            self._process_icp(handle, icp, icp_byte_count, raw_buffer)

    def _process_ipp(self, handle: int, raw_buffer: bytes):
        """Process an I/O Pending Packet."""
        in_startup = time.time() < self._startup_tolerance_until

        with self._protocol_lock:
            if self._tx_req_sent_size == 0:
                if in_startup:
                    _LOGGER.debug("Ignoring unexpected IPP during startup")
                    return
                _LOGGER.warning("Unexpected IPP (handle=0x%04x) - no request pending", handle)
                return

            req = self._dequeue_sent()
            if not req:
                return

            if handle == 0:
                _LOGGER.warning("Received zero handle - failing request")
                req.icp = ICP(handle=0, result=ErrorCode.ERR_INVALID_REQUEST)
                req.signal()
                return

            if handle in self._req_pending:
                _LOGGER.warning("Duplicate handle 0x%04x", handle)
                old_req = self._req_pending.pop(handle)
                old_req.icp = ICP(handle=0, result=ErrorCode.ERR_INVALID_REQUEST)
                old_req.signal()
                req.icp = ICP(handle=0, result=ErrorCode.ERR_INVALID_REQUEST)
                req.signal()
                return

            req.handle = handle
            self._req_pending[handle] = req

            if req.cancel:
                self._cancel_request_impl(req)

    def _process_icp(self, handle: int, icp: ICP, icp_byte_count: int, raw_buffer: bytes):
        """Process an I/O Completion Packet."""
        in_startup = time.time() < self._startup_tolerance_until

        with self._protocol_lock:
            req: Request | None = None

            if handle != 0:
                req = self._req_pending.pop(handle, None)
                if not req:
                    if time.time() < self._cancel_tolerance_until or in_startup:
                        _LOGGER.debug(
                            "ICP for unknown handle 0x%04x during tolerance period",
                            handle,
                        )
                        return
                    _LOGGER.warning("ICP for unknown handle 0x%04x - ignoring", handle)
                    return
            else:
                req = self._dequeue_sent()
                if not req:
                    if in_startup:
                        _LOGGER.debug("Ignoring synchronous ICP during startup")
                        return
                    _LOGGER.warning("Unexpected synchronous ICP - no request pending")
                    return

            # Validate ICP length
            if icp.result == ErrorCode.SUCCESS:
                if icp_byte_count != req.expected_icp_byte_count:
                    if in_startup:
                        _LOGGER.debug(
                            "ICP length mismatch for '%s' during startup: got %d, expected %d "
                            "— discarding stale ICP, keeping request alive",
                            req.req_str,
                            icp_byte_count,
                            req.expected_icp_byte_count,
                        )
                        if handle != 0:
                            self._req_pending[handle] = req
                        return
                    _LOGGER.warning(
                        "ICP length mismatch for '%s': got %d, expected %d — failing request",
                        req.req_str,
                        icp_byte_count,
                        req.expected_icp_byte_count,
                    )
                    req.icp = ICP(handle=handle, result=ErrorCode.ERR_SIZE_MISMATCH)
                    req.signal()
                    return
            elif icp_byte_count != 3:
                _LOGGER.warning(
                    "Error ICP has unexpected length %d (expected 3) for '%s'",
                    icp_byte_count,
                    req.req_str,
                )
                req.icp = ICP(handle=handle, result=ErrorCode.ERR_SIZE_MISMATCH)
                req.signal()
                return

            if icp.result == ErrorCode.ERR_OUT_OF_QUEUE:
                if self._tx_req_queued_size < self.MAX_REQUEST_QUEUED:
                    self._enqueue_queued(req)
                    return
                _LOGGER.warning("Cannot requeue - queue full")
                req.icp = ICP(handle=handle, result=ErrorCode.ERR_OUT_OF_QUEUE)
                req.signal()
                return

            req.icp = icp
            req.signal()

    def _process_queued_requests(self):
        """Process queued requests and send if possible."""
        with self._protocol_lock:
            self._remove_canceled_queued_requests()

            while (
                self._tx_req_queued_size > 0
                and (self._tx_req_sent_size + len(self._req_pending)) < self.MAX_REQUEST_COUNT
            ):
                req = self._dequeue_queued()
                if not req:
                    break

                state_good = self._state_good

                if not state_good:
                    req.icp = ICP(handle=0, result=ErrorCode.ERR_FAILSTATE)
                    req.signal()
                else:
                    req.queued = False
                    self._enqueue_sent(req)
                    self._write_to_buffer(req.irp, req.req_str)

    def _mark_communication_success(self):
        """Mark that we had a successful communication."""
        with self._protocol_lock:
            self._last_successful_communication = time.time()
            self._reconnect_attempts = 0

    # ================================================================================================
    # CANCEL OPERATIONS
    # ================================================================================================

    def _cancel_request_impl(self, req: Request):
        """Send a cancel IRP for a specific request."""
        cancel_params = encode_uint16(req.handle)
        cancel_irp = IRP(function=FunctionCode.CANCEL_IO, params=cancel_params)
        self._write_to_buffer(cancel_irp, "CANCEL_IO")

    async def cancel_all_io_requests(self):
        """Cancel all pending requests."""
        with self._protocol_lock:
            while self._tx_req_queued_size > 0:
                req = self._dequeue_queued()
                if req and not req.cancel:
                    req.icp = ICP(handle=0, result=ErrorCode.ERR_CANCELED)
                    req.signal()

            while self._tx_req_sent_size > 0:
                req = self._dequeue_sent()
                if req and not req.cancel:
                    req.icp = ICP(handle=0, result=ErrorCode.ERR_CANCELED)
                    req.signal()

            cancel_irp = IRP(function=FunctionCode.CANCEL_ALL_IO, params=b"")
            self._write_to_buffer(cancel_irp, "CANCEL_ALL_IO")

            for _handle, req in list(self._req_pending.items()):
                if not req.cancel:
                    req.icp = ICP(handle=0, result=ErrorCode.ERR_CANCELED)
                    req.signal()
            self._req_pending.clear()

            self._cancel_tolerance_until = time.time() + 2.0

    # ================================================================================================
    # HIGH-LEVEL API FUNCTIONS
    # ================================================================================================

    async def query_hw_version(self, timeout: float = 5.0) -> tuple[int, str]:
        """Query hardware version.

        Args:
            timeout: Query timeout in seconds. Use None for indefinite waiting.

        Returns:
            Tuple of (error_code, hw_version_string). The version string is
            empty on failure.
        """
        irp = IRP(function=FunctionCode.MA_QUERY_HW_VER, params=b"")
        req = self._create_request(irp, 1, 19, "MA_QUERY_HW_VER")

        self._place_request(req)
        if not await self._wait_for_request(req, timeout):
            return ErrorCode.ERR_RF_TIMEOUT, ""

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.MA_QUERY_HW_VER)
            hw_raw: bytes = parsed.get("hw_version_str", bytes(16))
            null_idx = hw_raw.find(0)
            if null_idx >= 0:
                hw_raw = hw_raw[:null_idx]
            return req.icp.result, hw_raw.decode("ascii", errors="ignore").strip()
        return req.icp.result, ""

    async def query_fw_version(self, timeout: float = 5.0) -> tuple[int, str]:
        """Query firmware version.

        Args:
            timeout: Query timeout in seconds. Use None for indefinite waiting.

        Returns:
            Tuple of (error_code, fw_version_string). The version string is
            formatted as "major.minor" (e.g. "1.4"), with " (incomplete)"
            appended when the firmware image is marked incomplete. Empty on
            failure.
        """
        irp = IRP(function=FunctionCode.MA_QUERY_FW_VER, params=b"")
        req = self._create_request(irp, 1, 6, "MA_QUERY_FW_VER")

        self._place_request(req)
        if not await self._wait_for_request(req, timeout):
            return ErrorCode.ERR_RF_TIMEOUT, ""

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.MA_QUERY_FW_VER)
            major = parsed.get("major_version", 0)
            minor = parsed.get("minor_version", 0)
            incomplete = parsed.get("incomplete_fw", False)
            fw_str = f"{major}.{minor}"
            if incomplete:
                fw_str += " (incomplete)"
            return req.icp.result, fw_str
        return req.icp.result, ""

    async def ping(self, timeout: float = 5.0) -> int:
        """Ping the module by sending an intentionally undefined command (0xF0).

        The RxModule firmware does not know function code 0xF0 and responds with
        ERR_INVALID_REQUEST (0x03).  Receiving *any* ICP response — even an error
        — proves the module is alive and the serial link is working.  This method
        therefore maps ERR_INVALID_REQUEST -> SUCCESS so that callers can treat a
        non-zero return value as a genuine communication failure.

        Args:
            timeout: Timeout in seconds waiting for the module's response.

        Returns:
            ErrorCode.SUCCESS (0)  — module responded (link is healthy)
            ErrorCode.ERR_RF_TIMEOUT — no response within *timeout* seconds
            Any other ErrorCode   — unexpected protocol or hardware error
        """
        irp = IRP(function=FunctionCode.PING_RCV, params=b"")
        req = self._create_request(irp, 1, 3, "PING_RCV")

        self._place_request(req)
        if not await self._wait_for_request(req, timeout):
            return ErrorCode.ERR_RF_TIMEOUT

        if req.icp.result == ErrorCode.ERR_INVALID_REQUEST:
            return ErrorCode.SUCCESS
        return req.icp.result

    # ================================================================================================
    # EASYWAVE BASIC API FUNCTIONS
    # ================================================================================================

    async def ew_get_fd_serial_request(self, index: int, timeout: float = 5.0) -> tuple[int, bytes]:
        """Get EW serial number at index.

        Args:
            timeout: Request timeout in seconds. Use None for indefinite waiting.
        """
        params = encode_uint16(index)
        irp = IRP(function=FunctionCode.EW_GET_FD_SERIAL, params=params)
        req = self._create_request(irp, 3, 19, "EW_GET_FD_SERIAL")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.EW_GET_FD_SERIAL)
            serial = parsed.get("gateway", bytes(16))
            return req.icp.result, serial
        return req.icp.result, bytes(16)

    async def ew_rcv_button_request(
        self, timeout: float | None = None
    ) -> tuple[int, int, bytes, bytes]:
        """Receive EW button press.

        Args:
            timeout: Read timeout in seconds. Use None for indefinite waiting.

        Returns:
            (result, info_type, transmitter, info_data)
        """
        irp = IRP(function=FunctionCode.EW_RCV_BUTTON, params=b"")
        req = self._create_request(irp, 1, 21, "EW_RCV_BUTTON")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.EW_RCV_BUTTON)
            info_type = parsed.get("info_type", 0)
            transmitter = parsed.get("receiver_or_transmitter", bytes(16))
            info_data = parsed.get("info_data", bytes(8))
            return req.icp.result, info_type, transmitter, info_data
        return req.icp.result, 0, bytes(16), bytes(8)

    async def ew_send_cmd_request(self, gateway: bytes, button: int, timeout: float = 5.0) -> int:
        """Send EW command.

        Args:
            timeout: Command timeout in seconds. Use None for indefinite waiting.
        """
        params = encode_serial_array(gateway) + bytes([button])
        irp = IRP(function=FunctionCode.EW_SEND_CMD, params=params)
        req = self._create_request(irp, 18, 3, "EW_SEND_CMD")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        return req.icp.result

    async def start_ew_send_cmd_loop(self, gateway: bytes, button: int) -> None:
        """Start continuous EW send command loop (dead man's switch)."""
        if self._send_cmd_loop_running:
            await self.stop_ew_send_cmd_loop()

        self._send_cmd_loop_gateway = gateway
        self._send_cmd_loop_button = button
        self._send_cmd_loop_running = True

        self._send_cmd_loop_task = asyncio.create_task(
            self._ew_send_cmd_loop(), name="RxModule-SendCmdLoop"
        )

    async def stop_ew_send_cmd_loop(self) -> None:
        """Stop continuous EW send command loop.

        Gracefully stops the loop and drains any pending requests.
        """
        self._send_cmd_loop_running = False
        # Signal drain mode: process remaining requests before exiting
        self._send_cmd_loop_drain = True

        if self._send_cmd_loop_task and not self._send_cmd_loop_task.done():
            try:
                await asyncio.wait_for(self._send_cmd_loop_task, timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._send_cmd_loop_task.cancel()
            self._send_cmd_loop_task = None

        # Reset drain flag and clear any remaining requests
        self._send_cmd_loop_drain = False
        with self._send_cmd_loop_lock:
            self._send_cmd_loop_queue.clear()
            self._send_cmd_loop_pending.clear()
            self._send_cmd_loop_consecutive_errors = 0

    def get_ew_send_cmd_loop_status(self) -> dict[str, Any]:
        """Get status and statistics of the EW send command loop.

        Returns:
            Dictionary with:
            - running: Whether loop is active
            - gateway: Current gateway address (hex string)
            - button: Current button index
            - queued: Number of commands prepared and waiting
            - pending: Number of commands awaiting completion
            - stats: Statistics (sent, success, errors, last_error)
            - last_error_time: When last error occurred
        """
        with self._send_cmd_loop_lock:
            return {
                "running": self._send_cmd_loop_running,
                "gateway": (
                    self._send_cmd_loop_gateway.hex() if self._send_cmd_loop_gateway else None
                ),
                "button": self._send_cmd_loop_button,
                "queued": len(self._send_cmd_loop_queue),
                "pending": len(self._send_cmd_loop_pending),
                "stats": self._send_cmd_loop_stats.copy(),
            }

    async def _ew_send_cmd_loop(self) -> None:
        """Internal pipeline loop for continuous EW send commands.

        Implements an asynchronous pipeline:
        1. Prepare upcoming requests in queue while previous ones execute
        2. Send queued requests asynchronously
        3. Monitor pending requests for completion
        4. Track errors and apply exponential backoff on failures
        5. Drain remaining requests gracefully on stop
        """
        try:
            while self._send_cmd_loop_running or self._send_cmd_loop_drain:
                if self._send_cmd_loop_gateway is None or self._send_cmd_loop_button is None:
                    await asyncio.sleep(0.01)
                    continue

                # Phase 1: Prepare new requests for the queue (pipeline ahead of execution)
                with self._send_cmd_loop_lock:
                    # Keep queue filled with pre-prepared requests (max 2 ahead)
                    max_queue_depth = 2
                    while (
                        len(self._send_cmd_loop_queue) < max_queue_depth
                        and self._send_cmd_loop_running
                    ):
                        # Create request but don't send yet
                        params = encode_serial_array(self._send_cmd_loop_gateway) + bytes(
                            [self._send_cmd_loop_button]
                        )
                        irp = IRP(function=FunctionCode.EW_SEND_CMD, params=params)
                        req = self._create_request(irp, 18, 3, "EW_SEND_CMD_LOOP")
                        self._send_cmd_loop_queue.append(req)

                # Phase 2: Monitor pending requests for completion
                with self._send_cmd_loop_lock:
                    completed: list[Request] = []
                    for req in self._send_cmd_loop_pending:
                        if req.completed:
                            completed.append(req)
                            # Process result
                            if req.icp.result == ErrorCode.SUCCESS:
                                self._send_cmd_loop_stats["success"] += 1
                                self._send_cmd_loop_consecutive_errors = 0  # Reset backoff
                            else:
                                self._send_cmd_loop_stats["errors"] += 1
                                self._send_cmd_loop_consecutive_errors += 1
                                self._send_cmd_loop_stats["last_error"] = f"0x{req.icp.result:02x}"
                                self._send_cmd_loop_stats["last_error_time"] = time.time()

                    # Remove completed requests
                    for req in completed:
                        self._send_cmd_loop_pending.remove(req)

                # Phase 3: Send next queued request if space available in pending
                with self._send_cmd_loop_lock:
                    max_pending = 3  # Allow up to 3 concurrent requests
                    if (
                        self._send_cmd_loop_queue
                        and len(self._send_cmd_loop_pending) < max_pending
                        and (self._send_cmd_loop_running or self._send_cmd_loop_drain)
                    ):
                        req = self._send_cmd_loop_queue.pop(0)
                        self._place_request(req)  # Send it
                        self._send_cmd_loop_pending.append(req)
                        self._send_cmd_loop_stats["sent"] += 1

                        # Apply backoff if we've had consecutive errors
                        if self._send_cmd_loop_consecutive_errors > 0:
                            backoff = min(
                                self._send_cmd_loop_backoff_delay
                                * (2 ** (self._send_cmd_loop_consecutive_errors - 1)),
                                self._send_cmd_loop_max_backoff,
                            )
                            _LOGGER.debug(
                                "EW_SEND_CMD_LOOP recovering from errors (consecutive: %d, backoff: %.2fs)",
                                self._send_cmd_loop_consecutive_errors,
                                backoff,
                            )
                            await asyncio.sleep(backoff)

                # Small sleep to prevent CPU spinning
                await asyncio.sleep(0.001)

        except Exception as e:
            _LOGGER.error("EW_SEND_CMD_LOOP fatal error: %s", e)
            self._send_cmd_loop_running = False
        finally:
            # Cleanup on exit
            with self._send_cmd_loop_lock:
                _LOGGER.info(
                    "EW_SEND_CMD_LOOP exiting. Stats: sent=%d, success=%d, errors=%d",
                    self._send_cmd_loop_stats["sent"],
                    self._send_cmd_loop_stats["success"],
                    self._send_cmd_loop_stats["errors"],
                )
                self._send_cmd_loop_queue.clear()
                self._send_cmd_loop_pending.clear()

    async def ew_rcv_ex_request(
        self, timeout: float | None = None
    ) -> tuple[int, int, bytes, bytes]:
        """Receive EW extended telegram.

        Args:
            timeout: Read timeout in seconds. Use None for indefinite waiting.

        Returns:
            (result, info_type, receiver, info_data)
        """
        irp = IRP(function=FunctionCode.EW_RCV_EX, params=b"")
        req = self._create_request(irp, 1, 28, "EW_RCV_EX")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.EW_RCV_EX)
            info_type = parsed.get("info_type", 0)
            transmitter = parsed.get("receiver_or_transmitter", bytes(16))
            info_data = parsed.get("info_data", bytes(8))
            return req.icp.result, info_type, transmitter, info_data
        return req.icp.result, 0, bytes(16), bytes(8)

    # ================================================================================================
    # EASYWAVE BIDI API FUNCTIONS
    # ================================================================================================

    async def ewb_get_fd_serial_request(
        self, index: int, timeout: float = 5.0
    ) -> tuple[int, bytes]:
        """Get EWB serial number at index."""
        params = encode_uint16(index)
        irp = IRP(function=FunctionCode.EWB_GET_FD_SERIAL, params=params)
        req = self._create_request(irp, 3, 19, "EWB_GET_FD_SERIAL")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.EWB_GET_FD_SERIAL)
            serial = parsed.get("gateway", bytes(16))
            return req.icp.result, serial
        return req.icp.result, bytes(16)

    async def ewb_add_nfilter_request(self, gateway: bytes, timeout: float = 5.0) -> int:
        """Add EWB gateway to filter.

        Args:
            gateway: Gateway serial number (16 bytes)
            timeout: Request timeout in seconds

        Returns:
            Error code
        """
        params = encode_serial_array(gateway)
        irp = IRP(function=FunctionCode.EWB_ADD_NFILTER, params=params)
        req = self._create_request(irp, 17, 3, "EWB_ADD_NFILTER")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        return req.icp.result

    async def ewb_clear_nfilter_request(self, timeout: float = 5.0) -> int:
        """Clear EWB filter.

        Args:
            timeout: Request timeout in seconds

        Returns:
            Error code
        """
        irp = IRP(function=FunctionCode.EWB_CLEAR_NFILTER, params=b"")
        req = self._create_request(irp, 1, 3, "EWB_CLEAR_NFILTER")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        return req.icp.result

    async def ewb_join_device_request(
        self, gateway: bytes, timeout: float = 30.0
    ) -> tuple[int, int, bytes]:
        """Join EWB device.

        Args:
            gateway: Gateway serial number (16 bytes)
            timeout: Request timeout in seconds (default 30s for learning)

        Returns:
            (result, device_type, receiver_serial)
        """
        params = encode_serial_array(gateway)
        irp = IRP(function=FunctionCode.EWB_JOIN_DEVICE, params=params)
        req = self._create_request(irp, 17, 20, "EWB_JOIN_DEVICE")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.EWB_JOIN_DEVICE)
            device_type = parsed.get("device_type", 0)
            receiver = parsed.get("receiver", bytes(16))
            return req.icp.result, device_type, receiver
        return req.icp.result, 0, bytes(16)

    async def ewb_remove_device_request(
        self, gateway: bytes, receiver: bytes, timeout: float = 5.0
    ) -> int:
        """Remove EWB device.

        Args:
            gateway: Gateway serial number (16 bytes)
            receiver: Receiver serial number (16 bytes)
            timeout: Request timeout in seconds

        Returns:
            Error code
        """
        params = encode_serial_array(gateway) + encode_serial_array(receiver)
        irp = IRP(function=FunctionCode.EWB_REMOVE_DEVICE, params=params)
        req = self._create_request(irp, 33, 3, "EWB_REMOVE_DEVICE")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        return req.icp.result

    async def ewb_rcv_request(self, timeout: float | None = None) -> tuple[int, int, bytes, bytes]:
        """Receive EWB telegram.

        Args:
            timeout: Read timeout in seconds. Use None for indefinite waiting.

        Returns:
            (result, info_type, receiver_transmitter, info_data)
        """
        irp = IRP(function=FunctionCode.EWB_RCV, params=b"")
        req = self._create_request(irp, 1, 28, "EWB_RCV")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.EWB_RCV)
            info_type = parsed.get("info_type", 0)
            receiver_transmitter = parsed.get("receiver_or_transmitter", bytes(16))
            info_data = parsed.get("info_data", bytes(8))
            return req.icp.result, info_type, receiver_transmitter, info_data
        return req.icp.result, 0, bytes(16), bytes(8)

    async def ewb_change_state_request(
        self,
        gateway: bytes,
        receiver: bytes,
        desired_mode: int,
        desired_state: bytes,
        timeout: float = 5.0,
    ) -> tuple[int, int, bytes]:
        """Change EWB device state.

        Args:
            gateway: Gateway serial number (16 bytes)
            receiver: Receiver serial number (16 bytes)
            desired_mode: Desired mode value
            desired_state: Desired state (4 bytes)
            timeout: Request timeout in seconds

        Returns:
            (result, recent_mode, recent_state)
        """
        params = (
            encode_serial_array(gateway)
            + encode_serial_array(receiver)
            + bytes([desired_mode])
            + desired_state
        )
        irp = IRP(function=FunctionCode.EWB_CHANGE_STATE, params=params)
        req = self._create_request(irp, 38, 8, "EWB_CHANGE_STATE")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.EWB_CHANGE_STATE)
            recent_mode = parsed.get("mode", 0)
            recent_state = parsed.get("state", bytes(4))
            return req.icp.result, recent_mode, recent_state
        return req.icp.result, 0, bytes(4)

    async def ewb_query_state_request(
        self,
        gateway: bytes,
        receiver: bytes,
        desired_mode: int,
        timeout: float = 5.0,
    ) -> tuple[int, int, bytes]:
        """Query EWB device state.

        Args:
            gateway: Gateway serial number (16 bytes)
            receiver: Receiver serial number (16 bytes)
            desired_mode: Mode to query
            timeout: Request timeout in seconds

        Returns:
            (result, recent_mode, state)
        """
        params = (
            encode_serial_array(gateway) + encode_serial_array(receiver) + bytes([desired_mode])
        )
        irp = IRP(function=FunctionCode.EWB_QUERY_STATE, params=params)
        req = self._create_request(irp, 34, 8, "EWB_QUERY_STATE")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.EWB_QUERY_STATE)
            recent_mode = parsed.get("mode", 0)
            state = parsed.get("state", bytes(4))
            return req.icp.result, recent_mode, state
        return req.icp.result, 0, bytes(4)

    async def ewb_tr_lrn_control_request(
        self,
        gateway: bytes,
        receiver: bytes,
        ctrl: int,
        desired_mode: int,
        desired_state: bytes,
        timeout: float = 30.0,
    ) -> tuple[int, int, bytes]:
        """Control EWB transmitter learning.

        Args:
            gateway: Gateway serial number (16 bytes)
            receiver: Receiver serial number (16 bytes)
            ctrl: Control code
            desired_mode: Desired mode
            desired_state: Desired state (4 bytes)
            timeout: Request timeout in seconds (default 30s for learning)

        Returns:
            (result, recent_mode, recent_state)
        """
        params = (
            encode_serial_array(gateway)
            + encode_serial_array(receiver)
            + bytes([ctrl, desired_mode])
            + desired_state
        )
        irp = IRP(function=FunctionCode.EWB_TRLRN_CONTROL, params=params)
        req = self._create_request(irp, 39, 8, "EWB_TRLRN_CONTROL")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.EWB_TRLRN_CONTROL)
            recent_mode = parsed.get("mode", 0)
            recent_state = parsed.get("state", bytes(4))
            return req.icp.result, recent_mode, recent_state
        return req.icp.result, 0, bytes(4)

    # ================================================================================================
    # SECURITY API FUNCTIONS
    # ================================================================================================

    async def sec_rcv_request(
        self, timeout: float | None = None
    ) -> tuple[int, int, int, int, int, int, int]:
        """Receive Secwave security telegram.

        Args:
            timeout: Read timeout in seconds. Use None for indefinite waiting.

        Returns:
            (result, stor_index, sec_query, sec_cmd, user_data, sec_flags, lrn_tel)
        """
        irp = IRP(function=FunctionCode.SEC_RCV, params=b"")
        req = self._create_request(irp, 1, 14, "SEC_RCV")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.SEC_RCV)
            stor_index = parsed.get("stor_index", 0)
            sec_query = parsed.get("sec_query", 0)
            sec_cmd = parsed.get("sec_cmd", 0)
            user_data = parsed.get("user_data", 0)
            sec_flags = parsed.get("sec_flags", 0)
            lrn_tel = parsed.get("lrn_tel", 0)
            return req.icp.result, stor_index, sec_query, sec_cmd, user_data, sec_flags, lrn_tel
        return req.icp.result, 0, 0, 0, 0, 0, 0

    async def sec_learn_request(
        self, user_data: int, timeout: float = 30.0
    ) -> tuple[int, int, int, int, int, int, int]:
        """Learn/program Secwave security storage entry.

        Args:
            user_data: 32-bit user data stored when a transmitter is learned
            timeout: Request timeout in seconds (default 30s for learning)

        Returns:
            (result, stor_index, sec_query, sec_cmd, user_data, sec_flags, lrn_tel)
        """
        params = encode_uint32(user_data)
        irp = IRP(function=FunctionCode.SEC_LEARN, params=params)
        req = self._create_request(irp, 5, 14, "SEC_LEARN")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.SEC_LEARN)
            stor_index = parsed.get("stor_index", 0)
            sec_query = parsed.get("sec_query", 0)
            sec_cmd = parsed.get("sec_cmd", 0)
            learned_user_data = parsed.get("user_data", 0)
            sec_flags = parsed.get("sec_flags", 0)
            lrn_tel = parsed.get("lrn_tel", 0)
            return (
                req.icp.result,
                stor_index,
                sec_query,
                sec_cmd,
                learned_user_data,
                sec_flags,
                lrn_tel,
            )
        return req.icp.result, 0, 0, 0, 0, 0, 0

    async def sec_stat_request(
        self, stor_index: int, timeout: float = 5.0
    ) -> tuple[int, bool, int]:
        """Query Secwave security storage entry status.

        Args:
            stor_index: Storage index (0-65535)
            timeout: Request timeout in seconds. Use None for indefinite waiting.

        Returns:
            (result, is_used, user_data)
        """
        params = encode_uint16(stor_index)
        irp = IRP(function=FunctionCode.SEC_STAT, params=params)
        req = self._create_request(irp, 3, 8, "SEC_STAT")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.SEC_STAT)
            is_used = parsed.get("is_used", False)
            user_data = parsed.get("user_data", 0)
            return req.icp.result, is_used, user_data
        return req.icp.result, False, 0

    async def sec_delete_request(
        self, stor_index: int, timeout: float = 5.0
    ) -> tuple[int, bool, int]:
        """Delete Secwave security storage entry.

        Args:
            stor_index: Storage index to delete (0-127)
            timeout: Request timeout in seconds. Use None for indefinite waiting.

        Returns:
            (result, is_used, user_data) — post-delete slot status from ICP
        """
        params = encode_uint16(stor_index)
        irp = IRP(function=FunctionCode.SEC_DELETE, params=params)
        req = self._create_request(irp, 3, 8, "SEC_DELETE")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.SEC_DELETE)
            is_used = parsed.get("is_used", False)
            user_data = parsed.get("user_data", 0)
            return req.icp.result, is_used, user_data
        return req.icp.result, False, 0

    async def sec_delete_all_request(self, timeout: float = 5.0) -> int:
        """Delete all Secwave security storage entries (factory reset).

        Args:
            timeout: Request timeout in seconds. Use None for indefinite waiting.

        Returns:
            Error code
        """
        irp = IRP(function=FunctionCode.SEC_DELETE_ALL, params=b"")
        req = self._create_request(irp, 1, 3, "SEC_DELETE_ALL")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        return req.icp.result

    async def sec_reply_query_request(
        self, primary_state: int, secondary_state: int, timeout: float = 5.0
    ) -> int:
        """Reply to a bidirectional Secwave query.

        Args:
            primary_state: Secwave primary state word (Spec Table 8)
            secondary_state: Secwave secondary state word (reserved, should be 0)
            timeout: Request timeout in seconds

        Returns:
            Error code
        """
        params = encode_uint16(primary_state) + encode_uint16(secondary_state)
        irp = IRP(function=FunctionCode.SEC_REPLY_QUERY, params=params)
        req = self._create_request(irp, 5, 3, "SEC_REPLY_QUERY")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        return req.icp.result

    async def sec_wr_userdata_request(
        self, stor_index: int, user_data: int, timeout: float = 5.0
    ) -> int:
        """Write user data to Secwave security storage entry.

        Args:
            stor_index: Storage index (0-65535)
            user_data: 32-bit user data to write
            timeout: Request timeout in seconds

        Returns:
            Error code
        """
        params = encode_uint16(stor_index) + encode_uint32(user_data)
        irp = IRP(function=FunctionCode.SEC_WR_USERDATA, params=params)
        req = self._create_request(irp, 7, 3, "SEC_WR_USERDATA")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        return req.icp.result

    async def sec_send_cmd_tel_request(
        self, params: bytes, timeout: float = 5.0
    ) -> tuple[int, int, int]:
        """Send Secwave command telegram.

        Args:
            params: 6-byte IRP payload from ``encode_sec_send_cmd_tel_params``
            timeout: Request timeout in seconds

        Returns:
            (result, primary_state, secondary_state) — reply state words when queried
        """
        if len(params) != 6:
            raise ValueError(f"SEC_SEND_CMD_TEL params must be 6 bytes, got {len(params)}")
        irp = IRP(function=FunctionCode.SEC_SEND_CMD_TEL, params=params)
        req = self._create_request(irp, 7, 7, "SEC_SEND_CMD_TEL")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.SEC_SEND_CMD_TEL)
            primary_state = parsed.get("primary_state", 0)
            secondary_state = parsed.get("secondary_state", 0)
            return req.icp.result, primary_state, secondary_state
        return req.icp.result, 0, 0

    async def sec_send_lrn_tel_request(
        self, params: bytes, timeout: float = 5.0
    ) -> tuple[int, int, int]:
        """Send Secwave learn/training telegram.

        Args:
            params: 6-byte IRP payload from ``encode_sec_send_cmd_tel_params``
            timeout: Request timeout in seconds

        Returns:
            (result, primary_state, secondary_state) — reply state words when queried
        """
        if len(params) != 6:
            raise ValueError(f"SEC_SEND_LRN_TEL params must be 6 bytes, got {len(params)}")
        irp = IRP(function=FunctionCode.SEC_SEND_LRN_TEL, params=params)
        req = self._create_request(irp, 7, 7, "SEC_SEND_LRN_TEL")

        self._place_request(req)
        await self._wait_for_request(req, timeout)

        if req.icp.result == ErrorCode.SUCCESS:
            parsed = parse_icp_data(req.icp, FunctionCode.SEC_SEND_LRN_TEL)
            primary_state = parsed.get("primary_state", 0)
            secondary_state = parsed.get("secondary_state", 0)
            return req.icp.result, primary_state, secondary_state
        return req.icp.result, 0, 0
