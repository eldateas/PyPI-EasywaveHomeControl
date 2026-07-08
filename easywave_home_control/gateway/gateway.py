"""RxModule transceiver gateway with EW / EWB / Secwave facades."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from ..codec import EwbRcvEvent
from ..protocols.rx11_rx2x.devices import RxModuleDevice
from ..protocols.rx11_rx2x.protocol import ErrorCode
from .base import BaseTransceiverGateway, GatewayCallbacks
from .capabilities import GatewayProtocol, TransceiverFamily
from .config import GatewayConfig
from .device_registry import create_rx_device
from .discovery import SERIAL_OR_OS_ERRORS
from .facades import EasywaveBasicFacade, EwbNeoFacade, SecwaveFacade
from .profiles import get_transceiver_profile

_LOGGER = logging.getLogger(__name__)


class RxModuleGateway(BaseTransceiverGateway):
    """Manage RxModule transceivers (RX11–RX25 and registered successors)."""

    ew: EasywaveBasicFacade
    ewb: EwbNeoFacade
    sec: SecwaveFacade

    def __init__(
        self,
        config: GatewayConfig | None = None,
        *,
        callbacks: GatewayCallbacks | None = None,
    ) -> None:
        config = config or GatewayConfig()
        profile = get_transceiver_profile(config.transceiver_id)
        if profile.family != TransceiverFamily.RX_MODULE:
            raise ValueError(
                f"RxModuleGateway requires an rx_module transceiver, got {config.transceiver_id!r}"
            )
        super().__init__(config, callbacks=callbacks, profile=profile)
        self._device: RxModuleDevice | None = None

        self.ew = EasywaveBasicFacade(self, GatewayProtocol.EW, self._profile)
        self.ewb = EwbNeoFacade(self, GatewayProtocol.EWB, self._profile)
        self.sec = SecwaveFacade(self, GatewayProtocol.SEC, self._profile)

    @property
    def device(self) -> RxModuleDevice | None:
        return self._device

    async def _connect_to_path(self, device_path: str) -> bool:
        try:
            self._device = create_rx_device(self._config.transceiver_id, device_path)  # type: ignore[arg-type]
            if not await self._device.connect():
                await self._cleanup_device()
                return False
            self._device_path = device_path
            await asyncio.sleep(self._config.settle_seconds)
            if not await self._ensure_versions_fetched():
                await self._cleanup_device()
                return False
            _LOGGER.info(
                "Connected to %s at %s (SN:%s, HW=%s, FW=%s)",
                self.transceiver_id,
                device_path,
                self._usb_serial_number,
                self._hw_version or "unknown",
                self._fw_version or "unknown",
            )
            self._bind_device_callbacks()
            await self._start_health_check()
            return True
        except SERIAL_OR_OS_ERRORS as err:
            _LOGGER.warning("Error connecting at %s: %s", device_path, err)
            await self._cleanup_device()
            return False

    async def _ensure_versions_fetched(self) -> bool:
        if not self._device:
            return False
        hw_version = await self._query_version_with_retry(
            self._device.query_hw_version,
            "hardware",
        )
        fw_version = await self._query_version_with_retry(
            self._device.query_fw_version,
            "firmware",
        )
        self._hw_version = hw_version
        self._fw_version = fw_version
        return not (hw_version is None and fw_version is None)

    async def _query_version_with_retry(
        self,
        query_method: Callable[..., Awaitable[tuple[int, str]]],
        label: str,
    ) -> str | None:
        retries = self._config.version_query_retries
        for attempt in range(retries):
            try:
                result, value = await query_method(timeout=self._config.request_timeout)
                if result == ErrorCode.SUCCESS and value:
                    return value
            except SERIAL_OR_OS_ERRORS:
                pass
            if attempt < retries - 1:
                await asyncio.sleep(self._config.version_query_retry_delay * (attempt + 1))
        return None

    async def _cancel_device_io(self) -> None:
        if self._device:
            await self._device.cancel_all_io_requests()

    async def _close_device(self) -> None:
        if self._device:
            await self._device.disconnect()

    def _bind_device_callbacks(self) -> None:
        if self._device:
            self._device.set_disconnect_callback(self._on_device_disconnect)
            self._device.set_reconnect_callback(None)

    def _clear_device_callbacks(self) -> None:
        if self._device:
            self._device.set_disconnect_callback(None)
            self._device.set_reconnect_callback(None)

    async def _receive_for_listen(self) -> EwbRcvEvent | None:
        return await self.ew.receive_ex()


EasywaveGateway = RxModuleGateway
