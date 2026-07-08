"""Secwave protocol facade."""

from __future__ import annotations

import logging
from typing import Union

from ...codec.secwave import (
    SecCommandTelegram,
    SecSendCmdTelRequest,
    SecSendCmdTelResponse,
    SecStorageEntry,
    encode_sec_send_cmd_tel_params,
    parse_sec_delete_result_with_index,
    parse_sec_learn_result,
    parse_sec_rcv_result,
    parse_sec_send_response,
    parse_sec_stat_result_with_index,
)
from ...protocols.rx11_rx2x.protocol import ErrorCode
from ._base import FacadeBase

_LOGGER = logging.getLogger(__name__)


class SecwaveFacade(FacadeBase):
    """SEC_RCV, storage management, and Secwave send telegrams."""

    async def receive(
        self,
        timeout: float | None = None,
    ) -> tuple[int, SecCommandTelegram | None] | None:
        self._ensure_supported()
        raw = await self._io.receive(
            lambda device, wait: device.sec_rcv_request(timeout=wait),
            timeout=timeout,
        )
        if raw is None:
            return None
        return parse_sec_rcv_result(raw)

    async def learn(
        self,
        user_data: int,
        *,
        timeout: float = 30.0,
    ) -> tuple[int, SecCommandTelegram | None] | None:
        self._ensure_supported()
        result = await self._io.request(
            lambda device: device.sec_learn_request(user_data, timeout=timeout)
        )
        if result is None:
            return None
        return parse_sec_learn_result(result)

    async def query_storage(
        self,
        storage_index: int,
    ) -> tuple[int, SecStorageEntry | None] | None:
        self._ensure_supported()
        result = await self._io.request(
            lambda device: device.sec_stat_request(
                storage_index,
                timeout=self._host.request_timeout,
            )
        )
        if result is None:
            return None
        return parse_sec_stat_result_with_index(storage_index, result)

    async def delete_storage(
        self,
        storage_index: int,
    ) -> tuple[int, SecStorageEntry | None] | None:
        self._ensure_supported()
        result = await self._io.request(
            lambda device: device.sec_delete_request(
                storage_index,
                timeout=self._host.request_timeout,
            )
        )
        if result is None:
            return None
        return parse_sec_delete_result_with_index(storage_index, result)

    async def delete_all_storage(self) -> bool:
        self._ensure_supported()
        result = await self._io.request(
            lambda device: device.sec_delete_all_request(
                timeout=self._host.request_timeout,
            )
        )
        return result == ErrorCode.SUCCESS

    async def reply_query(
        self,
        primary_state: int,
        secondary_state: int = 0,
    ) -> bool:
        self._ensure_supported()
        result = await self._io.request(
            lambda device: device.sec_reply_query_request(
                primary_state,
                secondary_state,
                timeout=self._host.request_timeout,
            )
        )
        return result == ErrorCode.SUCCESS

    async def write_user_data(self, storage_index: int, user_data: int) -> bool:
        self._ensure_supported()
        result = await self._io.request(
            lambda device: device.sec_wr_userdata_request(
                storage_index,
                user_data,
                timeout=self._host.request_timeout,
            )
        )
        return result == ErrorCode.SUCCESS

    async def send_command_telegram(
        self,
        request: Union[SecSendCmdTelRequest, bytes],
        *,
        timeout: float | None = None,
        queried_reply: bool = True,
    ) -> tuple[int, SecSendCmdTelResponse | None] | None:
        self._ensure_supported()
        params = (
            request
            if isinstance(request, bytes)
            else encode_sec_send_cmd_tel_params(request)
        )
        wait = self._host.request_timeout if timeout is None else timeout
        result = await self._io.request(
            lambda device: device.sec_send_cmd_tel_request(params, timeout=wait)
        )
        if result is None:
            return None
        error_code, primary_state, secondary_state = result
        if error_code != ErrorCode.SUCCESS:
            return error_code, None
        return error_code, parse_sec_send_response(
            primary_state,
            secondary_state,
            queried_reply=queried_reply,
        )

    async def send_learn_telegram(
        self,
        request: Union[SecSendCmdTelRequest, bytes],
        *,
        timeout: float | None = None,
        queried_reply: bool = True,
    ) -> tuple[int, SecSendCmdTelResponse | None] | None:
        self._ensure_supported()
        params = (
            request
            if isinstance(request, bytes)
            else encode_sec_send_cmd_tel_params(request)
        )
        wait = self._host.request_timeout if timeout is None else timeout
        result = await self._io.request(
            lambda device: device.sec_send_lrn_tel_request(params, timeout=wait)
        )
        if result is None:
            return None
        error_code, primary_state, secondary_state = result
        if error_code != ErrorCode.SUCCESS:
            return error_code, None
        return error_code, parse_sec_send_response(
            primary_state,
            secondary_state,
            queried_reply=queried_reply,
        )
