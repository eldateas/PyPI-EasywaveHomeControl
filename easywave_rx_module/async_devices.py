"""Async wrappers for RxModule and RX09 devices.

Provides async/await compatible interfaces for use with Home Assistant
and other async frameworks. Synchronous API is wrapped via ThreadPoolExecutor
to prevent blocking the event loop.

This is the PRIMARY API for Home Assistant integration.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from .protocols.base import BaseProtocol
from .protocols.rx09.devices import RX09Device
from .protocols.rx11_rx2x.devices import RxModuleDevice

_LOGGER = logging.getLogger(__name__)

# Shared executor for all async device operations
# This prevents blocking the event loop during serial operations
_DEFAULT_EXECUTOR = ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="easywave_rx_"
)


class AsyncDeviceBase:
    """Base async wrapper for all device types.

    Wraps synchronous device operations to work with asyncio event loops.
    All blocking serial I/O is executed in a thread pool.
    """

    def __init__(
        self,
        device: BaseProtocol,
        executor: ThreadPoolExecutor | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        """Initialize async wrapper.

        Args:
            device: Synchronous device instance to wrap
            executor: Optional custom ThreadPoolExecutor
            loop: Optional event loop (auto-detected if None)
        """
        self._device = device
        self._executor = executor or _DEFAULT_EXECUTOR
        self._loop = loop or asyncio.get_event_loop()

    def _run_in_executor(self, func: Callable, *args) -> asyncio.Future:
        """Run blocking function in thread pool without blocking event loop.

        Args:
            func: Synchronous function to execute
            *args: Arguments to pass to function

        Returns:
            Coroutine that can be awaited
        """
        return self._loop.run_in_executor(
            self._executor,
            func,
            *args
        )

    async def _async_call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute synchronous function asynchronously.

        Args:
            func: Synchronous function
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of function call
        """
        # Create wrapper that handles kwargs
        def wrapper():
            return func(*args, **kwargs)

        return await self._loop.run_in_executor(self._executor, wrapper)

    async def disconnect(self) -> None:
        """Disconnect from device gracefully."""
        try:
            await self._async_call(self._device.disconnect)
        except Exception as e:
            _LOGGER.warning("Error during disconnect: %s", e)

    async def get_device_info(self) -> dict[str, Any]:
        """Get device information asynchronously."""
        return await self._async_call(self._device.get_device_info)

    async def get_available_functions(self) -> dict[str, str]:
        """Get available functions asynchronously."""
        return await self._async_call(self._device.get_available_functions)

    async def ping_request(self, timeout: float = 5.0) -> bool:
        """Ping device asynchronously.

        Args:
            timeout: Timeout in seconds

        Returns:
            True if device responded, False on timeout
        """
        try:
            return await asyncio.wait_for(
                self._async_call(self._device.ping_request, timeout),
                timeout=timeout + 1.0  # Add 1s overhead for executor
            )
        except asyncio.TimeoutError:
            _LOGGER.warning("Device ping timeout after %.1f seconds", timeout)
            return False
        except Exception as e:
            _LOGGER.error("Device ping error: %s", e)
            return False


class AsyncRxModuleDevice(AsyncDeviceBase):
    """Async wrapper for RxModule family devices.

    Supports RX11, RX21, RX22, RX25 with async interfaces.
    """

    def __init__(
        self,
        device: RxModuleDevice,
        executor: ThreadPoolExecutor | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        """Initialize async RxModule wrapper."""
        super().__init__(device, executor, loop)
        self._device: RxModuleDevice = device

    # ========================================================================
    # EASYWAVE BASIC (EW) - ASYNC METHODS
    # ========================================================================

    async def ew_get_fd_serial_request(self, index: int) -> tuple[int, bytes]:
        """Get EW device serial number at index asynchronously.

        Args:
            index: Index in device list

        Returns:
            Tuple of (error_code, serial_bytes)
        """
        return await self._async_call(self._device.ew_get_fd_serial_request, index)

    async def ew_rcv_button_request(self) -> tuple[int, bytes]:
        """Wait for EW button press asynchronously.

        Returns:
            Tuple of (error_code, button_data)
        """
        return await self._async_call(self._device.ew_rcv_button_request)

    async def ew_send_cmd_request(
        self,
        gateway_id: int,
        button: int,
    ) -> tuple[int, bytes]:
        """Send EW command asynchronously.

        Args:
            gateway_id: Target gateway ID
            button: Button code (0-3)

        Returns:
            Tuple of (error_code, response_data)
        """
        return await self._async_call(
            self._device.ew_send_cmd_request,
            gateway_id,
            button
        )

    async def ew_rcv_ex_request(self) -> tuple[int, bytes]:
        """Receive extended EW telegram asynchronously.

        Returns:
            Tuple of (info_type, telegram_data)
        """
        return await self._async_call(self._device.ew_rcv_ex_request)

    # ========================================================================
    # EASYWAVE BIDI (EWB) - ASYNC METHODS
    # ========================================================================

    async def ewb_get_fd_serial_request(self, index: int) -> tuple[int, bytes]:
        """Get EWB device serial number at index asynchronously.

        Args:
            index: Index in filter

        Returns:
            Tuple of (error_code, serial_bytes)
        """
        return await self._async_call(self._device.ewb_get_fd_serial_request, index)

    async def ewb_rcv_request(self) -> tuple[int, bytes]:
        """Wait for EWB telegram reception asynchronously.

        Returns:
            Tuple of (error_code, telegram_data)
        """
        return await self._async_call(self._device.ewb_rcv_request)

    async def ewb_change_state_request(
        self,
        gateway_id: int,
        state: int,
    ) -> tuple[int, bytes]:
        """Change EWB device state asynchronously.

        Args:
            gateway_id: Target device gateway ID
            state: New state value

        Returns:
            Tuple of (error_code, response_data)
        """
        return await self._async_call(
            self._device.ewb_change_state_request,
            gateway_id,
            state
        )

    async def ewb_query_state_request(
        self,
        gateway_id: int,
    ) -> tuple[int, bytes]:
        """Query EWB device state asynchronously.

        Args:
            gateway_id: Target device gateway ID

        Returns:
            Tuple of (error_code, state_data)
        """
        return await self._async_call(
            self._device.ewb_query_state_request,
            gateway_id
        )

    # ========================================================================
    # SECWAVE (SEC) - ASYNC METHODS
    # ========================================================================

    async def sec_rcv_request(self) -> tuple[int, bytes]:
        """Wait for Secwave security telegram asynchronously.

        Returns:
            Tuple of (error_code, telegram_data)
        """
        return await self._async_call(self._device.sec_rcv_request)

    async def sec_learn_request(
        self,
        gateway_id: int,
        button: int,
    ) -> tuple[int, bytes]:
        """Learn/program Secwave security entry asynchronously.

        Args:
            gateway_id: Target gateway ID
            button: Button code

        Returns:
            Tuple of (error_code, response_data)
        """
        return await self._async_call(
            self._device.sec_learn_request,
            gateway_id,
            button
        )

    # ========================================================================
    # SYSTEM - ASYNC METHODS
    # ========================================================================

    async def query_hw_version(self) -> tuple[int, str]:
        """Query hardware version asynchronously.

        Returns:
            Tuple of (error_code, version_string)
        """
        return await self._async_call(self._device.query_hw_version)

    async def query_fw_version(self) -> tuple[int, str]:
        """Query firmware version asynchronously.

        Returns:
            Tuple of (error_code, version_string)
        """
        return await self._async_call(self._device.query_fw_version)


class AsyncRX09Device(AsyncDeviceBase):
    """Async wrapper for RX09 ASCII text protocol device.

    Supports non-blocking communication with RX09 basic receiver.
    """

    def __init__(
        self,
        device: RX09Device,
        executor: ThreadPoolExecutor | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        """Initialize async RX09 wrapper."""
        super().__init__(device, executor, loop)
        self._device: RX09Device = device

    # ========================================================================
    # RX09 SPECIFIC - ASYNC METHODS
    # ========================================================================

    async def get_device_id(self) -> tuple[int, dict]:
        """Get RX09 device identification asynchronously.

        Returns:
            Tuple of (result_code, id_dict)
        """
        return await self._async_call(self._device.get_device_id)

    async def query_positions(self) -> tuple[int, int]:
        """Query number of positions asynchronously.

        Returns:
            Tuple of (result_code, num_positions)
        """
        return await self._async_call(self._device.query_positions)

    async def read_position_data(self, position: int) -> tuple[int, int]:
        """Read position data asynchronously.

        Args:
            position: Position index

        Returns:
            Tuple of (result_code, serial_number)
        """
        return await self._async_call(self._device.read_position_data, position)

    async def send_telegramm(
        self,
        position: int,
        button: str,
    ) -> tuple[int, str]:
        """Send RX09 telegramm asynchronously.

        Args:
            position: Target position
            button: Button code ('A', 'B', 'C', 'D')

        Returns:
            Tuple of (result_code, response_string)
        """
        return await self._async_call(
            self._device.send_telegramm,
            position,
            button
        )

    async def receive_telegramm(self, timeout: float = 5.0) -> tuple[int, dict]:
        """Wait for RX09 telegramm reception asynchronously.

        Args:
            timeout: Timeout in seconds

        Returns:
            Tuple of (result_code, telegram_dict)
        """
        try:
            return await asyncio.wait_for(
                self._async_call(self._device.receive_telegramm, timeout),
                timeout=timeout + 1.0
            )
        except asyncio.TimeoutError:
            return (1, {"error": "timeout"})

    async def query_echo(self) -> tuple[int, bool]:
        """Query echo setting asynchronously.

        Returns:
            Tuple of (result_code, echo_enabled)
        """
        return await self._async_call(self._device.query_echo)

    async def set_echo(self, enabled: bool) -> tuple[int, str]:
        """Set echo mode asynchronously.

        Args:
            enabled: Enable/disable echo

        Returns:
            Tuple of (result_code, response_string)
        """
        return await self._async_call(self._device.set_echo, enabled)

    async def query_led(self) -> tuple[int, bool]:
        """Query LED status asynchronously.

        Returns:
            Tuple of (result_code, led_enabled)
        """
        return await self._async_call(self._device.query_led)

    async def set_led(self, enabled: bool) -> tuple[int, str]:
        """Set LED status asynchronously.

        Args:
            enabled: Enable/disable LED

        Returns:
            Tuple of (result_code, response_string)
        """
        return await self._async_call(self._device.set_led, enabled)

    async def query_button(self) -> tuple[int, str]:
        """Query button status asynchronously.

        Returns:
            Tuple of (result_code, button_code)
        """
        return await self._async_call(self._device.query_button)
