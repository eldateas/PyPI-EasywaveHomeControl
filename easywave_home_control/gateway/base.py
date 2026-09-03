"""Shared connection lifecycle for all transceiver gateways."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..codec import EwbRcvEvent
from ..serial_io import SERIAL_ERRORS
from .capabilities import TransceiverProfile
from .config import GatewayConfig
from .discovery import (
    SERIAL_OR_OS_ERRORS,
    async_find_usb_device,
    async_lookup_port_serial,
)
from .profiles import get_transceiver_profile

_LOGGER = logging.getLogger(__name__)

TelegramCallback = Callable[[EwbRcvEvent], Any]
StateCallback = Callable[[], Any]
ConnectCallback = Callable[["GatewayInfo"], Any]


class GatewayConnectionState(str, Enum):
    STOPPED = "stopped"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    STOPPING = "stopping"


@dataclass(frozen=True, slots=True)
class GatewayInfo:
    transceiver_id: str
    device_path: str
    usb_serial_number: str | None
    hw_version: str | None
    fw_version: str | None


@dataclass(slots=True)
class GatewayCallbacks:
    on_connected: ConnectCallback | None = None
    on_disconnected: StateCallback | None = None
    on_telegram: TelegramCallback | None = None
    on_device_swap: Callable[[str, str], Any] | None = None


class BaseTransceiverGateway(ABC):
    """Connection manager shared by RxModule and RX09 gateways."""

    def __init__(
        self,
        config: GatewayConfig | None = None,
        *,
        callbacks: GatewayCallbacks | None = None,
        profile: TransceiverProfile | None = None,
    ) -> None:
        self._config = config or GatewayConfig()
        self._callbacks = callbacks or GatewayCallbacks()
        self._profile = profile or get_transceiver_profile(self._config.transceiver_id)

        self._state = GatewayConnectionState.STOPPED
        self._device: Any = None
        self._device_path: str | None = self._config.port
        self._usb_serial_number: str | None = None
        self._hw_version: str | None = None
        self._fw_version: str | None = None
        self._last_disconnect_time: float | None = None
        self._reconnect_attempts = 0

        self._lock = asyncio.Lock()
        self._io_cancel_lock = asyncio.Lock()
        self._health_task: asyncio.Task[None] | None = None
        self._reconnect_task: asyncio.Task[None] | None = None
        self._listen_task: asyncio.Task[None] | None = None
        self._health_stopping = False
        self._listen_stopping = False
        self._reconnect_stopping = False

    @property
    def profile(self) -> TransceiverProfile:
        return self._profile

    @property
    def transceiver_id(self) -> str:
        return self._profile.id

    @property
    def config(self) -> GatewayConfig:
        return self._config

    @property
    def state(self) -> GatewayConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == GatewayConnectionState.CONNECTED

    @property
    def device_path(self) -> str | None:
        return self._device_path

    @property
    def usb_serial_number(self) -> str | None:
        return self._usb_serial_number

    @property
    def hw_version(self) -> str | None:
        return self._hw_version

    @property
    def fw_version(self) -> str | None:
        return self._fw_version

    @property
    def request_timeout(self) -> float:
        return self._config.request_timeout

    @property
    def listen_timeout(self) -> float:
        return self._config.listen_timeout

    @property
    def io_cancel_lock(self) -> asyncio.Lock:
        return self._io_cancel_lock

    @property
    def device(self) -> Any:
        return self._device

    @property
    def info(self) -> GatewayInfo | None:
        if not self.is_connected or self._device_path is None:
            return None
        return GatewayInfo(
            transceiver_id=self.transceiver_id,
            device_path=self._device_path,
            usb_serial_number=self._usb_serial_number,
            hw_version=self._hw_version,
            fw_version=self._fw_version,
        )

    def supports(self, protocol: Any) -> bool:
        return self._profile.supports_protocol(protocol)

    async def start(self) -> bool:
        async with self._lock:
            if self._state not in (
                GatewayConnectionState.STOPPED,
                GatewayConnectionState.DISCONNECTED,
            ):
                return self.is_connected
            self._state = GatewayConnectionState.CONNECTING

        connected = await self.connect()
        if self._config.auto_reconnect:
            await self._start_reconnect_monitor()
        return connected

    async def stop(self) -> None:
        async with self._lock:
            if self._state == GatewayConnectionState.STOPPED:
                return
            self._state = GatewayConnectionState.STOPPING

        await self._stop_reconnect_monitor()
        await self._stop_listen()
        await self._stop_health_check()
        await self._disconnect_device()
        self._state = GatewayConnectionState.STOPPED

    async def connect(self) -> bool:
        async with self._lock:
            if self.is_connected:
                return True
            self._state = GatewayConnectionState.CONNECTING

        try:
            if self._device_path:
                if not await self._connect_to_path(self._device_path):
                    self._enter_disconnected()
                    return False
            elif self._profile.usb_discovery:
                port_info = await async_find_usb_device(
                    self._profile.usb_ids,
                    baudrate=self._profile.default_baudrate,
                )
                if port_info is None:
                    if self._reconnect_attempts == 0:
                        _LOGGER.warning("%s device not found", self.transceiver_id)
                    self._enter_disconnected()
                    return False
                device_path, serial_number = port_info
                self._device_path = device_path
                self._usb_serial_number = serial_number
                if not await self._connect_to_path(device_path):
                    self._enter_disconnected()
                    return False
            else:
                _LOGGER.warning(
                    "%s requires an explicit port (no USB discovery)",
                    self.transceiver_id,
                )
                self._enter_disconnected()
                return False

            await self._refresh_usb_identity()
            self._reconnect_attempts = 0
            self._state = GatewayConnectionState.CONNECTED
            await self._invoke_callback(self._callbacks.on_connected, self.info)
            if self._config.auto_listen and self._callbacks.on_telegram:
                await self._start_listen()
            return True
        except SERIAL_OR_OS_ERRORS as err:
            _LOGGER.debug("Cannot connect to gateway: %s", err)
            self._enter_disconnected()
            return False

    async def disconnect(self) -> None:
        async with self._lock:
            await self._stop_listen()
            await self._stop_health_check()
            await self._disconnect_device()
            self._enter_disconnected()

    async def reconnect(self) -> bool:
        if self._state == GatewayConnectionState.STOPPED:
            return False
        if self._last_disconnect_time:
            elapsed = time.time() - self._last_disconnect_time
            delay = self._config.reconnect_min_delay_after_disconnect - elapsed
            if delay > 0:
                await asyncio.sleep(delay)
        await self.disconnect()
        self._reconnect_attempts += 1
        return await self.connect()

    async def cancel_pending_receives(self) -> None:
        if not self._device or not self.is_connected:
            return
        async with self._io_cancel_lock:
            with contextlib.suppress(SERIAL_OR_OS_ERRORS):
                await self._cancel_device_io()

    async def suspend_listen(self) -> None:
        await self._stop_listen()
        await self.cancel_pending_receives()

    async def resume_listen(self) -> None:
        if self._config.auto_listen and self._callbacks.on_telegram and self.is_connected:
            await self._start_listen()

    @abstractmethod
    async def _connect_to_path(self, device_path: str) -> bool: ...

    @abstractmethod
    async def _ensure_versions_fetched(self) -> bool: ...

    @abstractmethod
    async def _cancel_device_io(self) -> None: ...

    @abstractmethod
    async def _close_device(self) -> None: ...

    @abstractmethod
    def _bind_device_callbacks(self) -> None: ...

    @abstractmethod
    def _clear_device_callbacks(self) -> None: ...

    @abstractmethod
    async def _receive_for_listen(self) -> EwbRcvEvent | None: ...

    async def _disconnect_device(self) -> None:
        if self._device:
            self._clear_device_callbacks()
            await self._close_device()
            self._device = None
        self._last_disconnect_time = time.time()

    async def _cleanup_device(self) -> None:
        await self._stop_health_check()
        if self._device:
            await self._close_device()
            self._device = None

    def _enter_disconnected(self) -> None:
        if self._state != GatewayConnectionState.STOPPING:
            self._state = GatewayConnectionState.DISCONNECTED

    async def _refresh_usb_identity(self) -> None:
        if not self._device_path:
            return
        serial_number = await async_lookup_port_serial(self._device_path)
        if not serial_number:
            return
        old_serial = self._usb_serial_number
        self._usb_serial_number = serial_number
        if old_serial and old_serial != serial_number:
            _LOGGER.info("Device swap detected: %s -> %s", old_serial, serial_number)
            self._hw_version = None
            self._fw_version = None
            await self._invoke_callback(
                self._callbacks.on_device_swap,
                old_serial,
                serial_number,
            )

    async def _start_health_check(self) -> None:
        if self._health_task:
            return
        self._health_stopping = False
        self._health_task = asyncio.create_task(
            self._health_check_loop(),
            name=f"{self.transceiver_id.lower()}-gateway-health",
        )

    async def _stop_health_check(self) -> None:
        self._health_stopping = True
        if not self._health_task:
            return
        task = self._health_task
        self._health_task = None
        if task is not asyncio.current_task():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def _health_check_loop(self) -> None:
        try:
            consecutive_failures = 0
            max_failures = self._config.health_check_max_failures
            while not self._health_stopping:
                await asyncio.sleep(self._config.health_check_interval)
                device = self._device
                if not self.is_connected or device is None:
                    consecutive_failures = 0
                    continue
                connected = False
                async with self._io_cancel_lock:
                    with contextlib.suppress(SERIAL_OR_OS_ERRORS):
                        connected = await device.ping_request(timeout=self._config.request_timeout)
                if connected:
                    consecutive_failures = 0
                    continue
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    await self._handle_connection_lost()
                    break
        except asyncio.CancelledError:
            pass
        finally:
            self._health_task = None

    async def _start_reconnect_monitor(self) -> None:
        if self._reconnect_task:
            return
        self._reconnect_stopping = False
        self._reconnect_task = asyncio.create_task(
            self._reconnect_monitor_loop(),
            name=f"{self.transceiver_id.lower()}-gateway-reconnect",
        )

    async def _stop_reconnect_monitor(self) -> None:
        self._reconnect_stopping = True
        if not self._reconnect_task:
            return
        task = self._reconnect_task
        self._reconnect_task = None
        if task is not asyncio.current_task():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def _reconnect_monitor_loop(self) -> None:
        try:
            while not self._reconnect_stopping:
                await asyncio.sleep(self._config.reconnect_interval)
                if self._reconnect_stopping or self.is_connected:
                    continue
                if self._state == GatewayConnectionState.STOPPING:
                    break
                await self.reconnect()
        except asyncio.CancelledError:
            pass
        finally:
            self._reconnect_task = None

    async def _start_listen(self) -> None:
        if self._listen_task or not self._callbacks.on_telegram:
            return
        self._listen_stopping = False
        self._listen_task = asyncio.create_task(
            self._listen_loop(),
            name=f"{self.transceiver_id.lower()}-gateway-listen",
        )

    async def _stop_listen(self) -> None:
        self._listen_stopping = True
        if not self._listen_task:
            return
        task = self._listen_task
        self._listen_task = None
        if task is not asyncio.current_task():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def _listen_loop(self) -> None:
        callback = self._callbacks.on_telegram
        if callback is None:
            return
        try:
            while not self._listen_stopping and self.is_connected:
                try:
                    telegram = await self._receive_for_listen()
                    if telegram is not None:
                        await self._invoke_callback(callback, telegram)
                except asyncio.CancelledError:
                    break
                except SERIAL_OR_OS_ERRORS:
                    await asyncio.sleep(5.0)
        finally:
            self._listen_task = None

    async def _handle_connection_lost(self) -> None:
        was_connected = self.is_connected
        async with self._lock:
            if not was_connected:
                return
            await self._stop_listen()
            await self._stop_health_check()
            await self._disconnect_device()
            self._enter_disconnected()
        if was_connected:
            await self._invoke_callback(self._callbacks.on_disconnected)

    def _on_device_disconnect(self) -> None:
        def _schedule() -> None:
            asyncio.create_task(self._handle_connection_lost())

        try:
            asyncio.get_running_loop().call_soon_threadsafe(_schedule)
        except RuntimeError:
            pass

    @staticmethod
    async def _invoke_callback(callback: Callable[..., Any] | None, *args: Any) -> None:
        if callback is None:
            return
        try:
            result = callback(*args)
            if hasattr(result, "__await__"):
                await result  # type: ignore[misc]
        except (OSError, RuntimeError) as err:
            _LOGGER.warning("Gateway callback error: %s", err)

    async def _close_device_quietly(self) -> None:
        with contextlib.suppress(*SERIAL_ERRORS):
            await self._close_device()
