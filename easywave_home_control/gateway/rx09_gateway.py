"""RX09 ASCII transceiver gateway (Easywave Basic only)."""

from __future__ import annotations

import logging
from typing import Any

from ..codec import EwbRcvEvent
from ..protocols.rx09.devices import RX09Device
from ..protocols.rx09.protocol import ErrorCode as RX09ErrorCode
from ..protocols.rx09.parsing import parse_rec_message
from .base import BaseTransceiverGateway, GatewayCallbacks
from .capabilities import GatewayProtocol, TransceiverFamily, UnsupportedProtocolError
from .config import GatewayConfig
from .discovery import SERIAL_OR_OS_ERRORS
from .facades._base import FacadeBase
from .profiles import get_transceiver_profile

_LOGGER = logging.getLogger(__name__)


class _UnsupportedFacade:
    def __init__(self, transceiver_id: str, protocol: GatewayProtocol) -> None:
        self._transceiver_id = transceiver_id
        self._protocol = protocol

    def __getattr__(self, name: str) -> Any:
        raise UnsupportedProtocolError(self._transceiver_id, self._protocol)


class Rx09EasywaveFacade(FacadeBase):
    """ASCII Easywave Basic commands for RX09."""

    async def send_telegram(self, position: int, button: str) -> bool:
        self._ensure_supported()
        result = await self._io.request(
            lambda device: device.send_telegramm(
                position,
                button,
                timeout=self._host.request_timeout,
            )
        )
        return result == RX09ErrorCode.SUCCESS

    async def receive_telegram(self, timeout: float | None = None) -> dict[str, Any] | None:
        self._ensure_supported()
        raw = await self._io.receive(
            lambda device, wait: device.receive_telegramm(timeout=wait),
            timeout=timeout,
        )
        if raw is None:
            return None
        error_code, message = raw
        if error_code != RX09ErrorCode.SUCCESS or not message:
            return None
        try:
            return parse_rec_message(message)
        except (ValueError, KeyError) as err:
            _LOGGER.debug("Failed to parse RX09 REC: %s", err)
            return None


class Rx09Gateway(BaseTransceiverGateway):
    """Gateway for RX09 with Easywave Basic only."""

    ew: Rx09EasywaveFacade
    ewb: _UnsupportedFacade
    sec: _UnsupportedFacade

    def __init__(
        self,
        config: GatewayConfig | None = None,
        *,
        callbacks: GatewayCallbacks | None = None,
    ) -> None:
        config = config or GatewayConfig(transceiver_id="RX09")
        profile = get_transceiver_profile(config.transceiver_id)
        if profile.family != TransceiverFamily.RX09:
            raise ValueError(
                f"Rx09Gateway requires transceiver_id RX09, got {config.transceiver_id!r}"
            )
        super().__init__(config, callbacks=callbacks, profile=profile)
        self._device: RX09Device | None = None
        self.ew = Rx09EasywaveFacade(self, GatewayProtocol.EW, self._profile)
        self.ewb = _UnsupportedFacade(self.transceiver_id, GatewayProtocol.EWB)
        self.sec = _UnsupportedFacade(self.transceiver_id, GatewayProtocol.SEC)

    @property
    def device(self) -> RX09Device | None:
        return self._device

    async def _connect_to_path(self, device_path: str) -> bool:
        try:
            self._device = RX09Device(port=device_path)
            if not await self._device.connect():
                await self._cleanup_device()
                return False
            self._device_path = device_path
            if not await self._ensure_versions_fetched():
                await self._cleanup_device()
                return False
            _LOGGER.info("Connected to RX09 at %s (id=%s)", device_path, self._hw_version)
            await self._start_health_check()
            return True
        except SERIAL_OR_OS_ERRORS as err:
            _LOGGER.warning("Error connecting to RX09 at %s: %s", device_path, err)
            await self._cleanup_device()
            return False

    async def _ensure_versions_fetched(self) -> bool:
        if not self._device:
            return False
        result, device_id = await self._device.get_device_id(timeout=self._config.request_timeout)
        if result == RX09ErrorCode.SUCCESS and device_id:
            self._hw_version = str(device_id)
            return True
        return False

    async def _cancel_device_io(self) -> None:
        return

    async def _close_device(self) -> None:
        if self._device:
            await self._device.disconnect()

    def _bind_device_callbacks(self) -> None:
        return

    def _clear_device_callbacks(self) -> None:
        return

    async def _receive_for_listen(self) -> EwbRcvEvent | None:
        # RX09 uses a different telegram shape; integrations should use gateway.ew.receive_telegram.
        return None
