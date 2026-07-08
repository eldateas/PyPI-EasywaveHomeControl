"""IO helpers shared by gateway protocol facades."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Protocol, TypeVar

from ..protocols.rx11_rx2x.devices import RxModuleDevice
from .discovery import SERIAL_OR_OS_ERRORS

if TYPE_CHECKING:
    from .gateway import RxModuleGateway

_LOGGER = logging.getLogger(__name__)
T = TypeVar("T")


class GatewayIOHost(Protocol):
    """Subset of :class:`RxModuleGateway` used by protocol facades."""

    @property
    def is_connected(self) -> bool: ...

    @property
    def device(self) -> RxModuleDevice | None: ...

    @property
    def request_timeout(self) -> float: ...

    @property
    def listen_timeout(self) -> float: ...

    @property
    def io_cancel_lock(self) -> asyncio.Lock: ...

    async def cancel_pending_receives(self) -> None: ...


class GatewayIO:
    """Run device requests with consistent locking and error handling."""

    def __init__(self, host: GatewayIOHost) -> None:
        self._host = host

    @property
    def _device(self) -> RxModuleDevice | None:
        if not self._host.is_connected:
            return None
        return self._host.device

    async def request(
        self,
        operation: Callable[[RxModuleDevice], Awaitable[T]],
        *,
        timeout: float | None = None,
        locked: bool = True,
    ) -> T | None:
        """Run a short request (send, query, learn, …)."""
        device = self._device
        if device is None:
            return None

        async def _run() -> T:
            return await operation(device)

        if not locked:
            try:
                return await _run()
            except SERIAL_OR_OS_ERRORS as err:
                _LOGGER.debug("Gateway request failed: %s", err)
                return None

        async with self._host.io_cancel_lock:
            try:
                return await _run()
            except SERIAL_OR_OS_ERRORS as err:
                _LOGGER.debug("Gateway request failed: %s", err)
                return None

    async def receive(
        self,
        operation: Callable[[RxModuleDevice, float | None], Awaitable[T]],
        *,
        timeout: float | None = None,
    ) -> T | None:
        """Run a blocking receive; flush orphaned requests after timeout."""
        device = self._device
        if device is None:
            return None
        wait_timeout = self._host.listen_timeout if timeout is None else timeout
        try:
            return await operation(device, wait_timeout)
        except TimeoutError:
            _LOGGER.debug("Gateway receive timed out")
        except SERIAL_OR_OS_ERRORS as err:
            _LOGGER.debug("Gateway receive failed: %s", err)
        with contextlib.suppress(SERIAL_OR_OS_ERRORS):
            await self._host.cancel_pending_receives()
        return None
