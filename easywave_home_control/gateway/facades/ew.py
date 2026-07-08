"""Easywave Basic (EW) protocol facade."""

from __future__ import annotations

import logging

from ...codec import EwbRcvEvent, parse_ew_rcv_ex_result
from ...codec.exceptions import CodecError
from ...protocols.rx11_rx2x.protocol import ErrorCode
from ._base import FacadeBase

_LOGGER = logging.getLogger(__name__)


class EasywaveBasicFacade(FacadeBase):
    """EW_GET_FD_SERIAL, EW_SEND_CMD, EW_RCV_*, and send-command loop."""

    async def get_gateway_serial(self, index: int) -> bytes | None:
        self._ensure_supported()
        result = await self._io.request(
            lambda device: device.ew_get_fd_serial_request(
                index,
                timeout=self._host.request_timeout,
            )
        )
        if result is None:
            return None
        error_code, serial_bytes = result
        if error_code == ErrorCode.SUCCESS and serial_bytes != bytes(16):
            return serial_bytes
        return None

    async def send_command(self, gateway: bytes, button: int) -> bool:
        self._ensure_supported()
        result = await self._io.request(
            lambda device: device.ew_send_cmd_request(
                gateway,
                button,
                timeout=self._host.request_timeout,
            )
        )
        return result == ErrorCode.SUCCESS

    async def start_send_loop(self, gateway: bytes, button: int) -> bool:
        self._ensure_supported()
        async def _start(device):
            await device.start_ew_send_cmd_loop(gateway, button)
            return True

        return (await self._io.request(_start)) is True

    async def stop_send_loop(self) -> bool:
        self._ensure_supported()
        async def _stop(device):
            await device.stop_ew_send_cmd_loop()
            return True

        return (await self._io.request(_stop)) is True

    async def receive_button(self, timeout: float | None = None) -> EwbRcvEvent | None:
        self._ensure_supported()
        raw = await self._io.receive(
            lambda device, wait: device.ew_rcv_button_request(timeout=wait),
            timeout=timeout,
        )
        return self._parse_raw(raw)

    async def receive_ex(self, timeout: float | None = None) -> EwbRcvEvent | None:
        """Receive EW_RCV_EX (buttons, neo sensors, and other EW telegrams)."""
        self._ensure_supported()
        raw = await self._io.receive(
            lambda device, wait: device.ew_rcv_ex_request(timeout=wait),
            timeout=timeout,
        )
        return self._parse_raw(raw)

    @staticmethod
    def _parse_raw(raw: tuple[int, int, bytes, bytes] | None) -> EwbRcvEvent | None:
        if raw is None:
            return None
        error_code, event = parse_ew_rcv_ex_result(raw)
        if error_code != ErrorCode.SUCCESS or event is None:
            return None
        try:
            return event
        except CodecError as err:
            _LOGGER.debug("Failed to parse EW telegram: %s", err)
            return None
