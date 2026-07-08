"""Easywave Bidi neo (EWB) protocol facade."""

from __future__ import annotations

import logging
from typing import Any

from ...codec import (
    EwbRcvEvent,
    EwbState,
    StateDirection,
    encode_ewb_state,
    parse_ewb_rcv_result,
    parse_ewb_state,
)
from ...codec.exceptions import CodecError
from ...protocols.rx11_rx2x.protocol import ErrorCode
from ._base import FacadeBase

_LOGGER = logging.getLogger(__name__)


class EwbNeoFacade(FacadeBase):
    """EWB pairing, state control, and EWB_RCV telegrams."""

    async def get_gateway_serial(self, index: int) -> bytes | None:
        self._ensure_supported()
        result = await self._io.request(
            lambda device: device.ewb_get_fd_serial_request(
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

    async def add_gateway_filter(self, gateway: bytes) -> bool:
        self._ensure_supported()
        result = await self._io.request(
            lambda device: device.ewb_add_nfilter_request(
                gateway,
                timeout=self._host.request_timeout,
            )
        )
        return result == ErrorCode.SUCCESS

    async def clear_gateway_filter(self) -> bool:
        self._ensure_supported()
        result = await self._io.request(
            lambda device: device.ewb_clear_nfilter_request(
                timeout=self._host.request_timeout,
            )
        )
        return result == ErrorCode.SUCCESS

    async def join_device(
        self,
        gateway: bytes,
        *,
        timeout: float = 30.0,
    ) -> tuple[int, bytes] | None:
        """Pair a neo receiver. Returns ``(device_type, receiver_serial)``."""
        self._ensure_supported()
        result = await self._io.request(
            lambda device: device.ewb_join_device_request(gateway, timeout=timeout)
        )
        if result is None:
            return None
        error_code, device_type, receiver = result
        if error_code != ErrorCode.SUCCESS:
            return None
        return device_type, receiver

    async def remove_device(self, gateway: bytes, receiver: bytes) -> bool:
        self._ensure_supported()
        result = await self._io.request(
            lambda device: device.ewb_remove_device_request(
                gateway,
                receiver,
                timeout=self._host.request_timeout,
            )
        )
        return result == ErrorCode.SUCCESS

    async def receive(
        self,
        *,
        device_type: int | None = None,
        timeout: float | None = None,
    ) -> EwbRcvEvent | None:
        """Receive EWB_RCV (neo receiver events and state notifications)."""
        self._ensure_supported()
        raw = await self._io.receive(
            lambda device, wait: device.ewb_rcv_request(timeout=wait),
            timeout=timeout,
        )
        if raw is None:
            return None
        try:
            return parse_ewb_rcv_result(raw, device_type=device_type)
        except CodecError as err:
            _LOGGER.debug("Failed to parse EWB telegram: %s", err)
            return None

    async def change_state(
        self,
        gateway: bytes,
        receiver: bytes,
        device_type: int,
        mode: int,
        command: Any,
        *,
        timeout: float | None = None,
    ) -> tuple[int, EwbState | None] | None:
        """Encode ``command``, send EWB_CHANGE_STATE, return parsed recent state."""
        self._ensure_supported()
        desired_state = encode_ewb_state(
            device_type,
            mode,
            command,
            direction=StateDirection.TO_DEVICE,
        )
        wait = self._host.request_timeout if timeout is None else timeout
        result = await self._io.request(
            lambda device: device.ewb_change_state_request(
                gateway,
                receiver,
                mode,
                desired_state,
                timeout=wait,
            )
        )
        if result is None:
            return None
        error_code, recent_mode, recent_state = result
        if error_code != ErrorCode.SUCCESS:
            return error_code, None
        return error_code, parse_ewb_state(
            device_type,
            recent_mode,
            recent_state,
            direction=StateDirection.FROM_DEVICE,
        )

    async def query_state(
        self,
        gateway: bytes,
        receiver: bytes,
        device_type: int,
        mode: int,
        *,
        timeout: float | None = None,
    ) -> tuple[int, EwbState | None] | None:
        self._ensure_supported()
        wait = self._host.request_timeout if timeout is None else timeout
        result = await self._io.request(
            lambda device: device.ewb_query_state_request(
                gateway,
                receiver,
                mode,
                timeout=wait,
            )
        )
        if result is None:
            return None
        error_code, recent_mode, state_bytes = result
        if error_code != ErrorCode.SUCCESS:
            return error_code, None
        return error_code, parse_ewb_state(
            device_type,
            recent_mode,
            state_bytes,
            direction=StateDirection.FROM_DEVICE,
        )

    async def transmitter_learn_control(
        self,
        gateway: bytes,
        receiver: bytes,
        device_type: int,
        ctrl: int,
        mode: int,
        command: Any,
        *,
        timeout: float = 30.0,
    ) -> tuple[int, EwbState | None] | None:
        self._ensure_supported()
        desired_state = encode_ewb_state(
            device_type,
            mode,
            command,
            direction=StateDirection.TO_DEVICE,
        )
        result = await self._io.request(
            lambda device: device.ewb_tr_lrn_control_request(
                gateway,
                receiver,
                ctrl,
                mode,
                desired_state,
                timeout=timeout,
            )
        )
        if result is None:
            return None
        error_code, recent_mode, recent_state = result
        if error_code != ErrorCode.SUCCESS:
            return error_code, None
        return error_code, parse_ewb_state(
            device_type,
            recent_mode,
            recent_state,
            direction=StateDirection.FROM_DEVICE,
        )
