"""Secwave codec — parse/encode for Secwave transmitters and receivers."""

from __future__ import annotations

from .commands import SecwaveCommand
from .fields import SecLearnTelegramKind, SecQuery, SecTransmitterFlags
from .irp import (
    MAX_STORAGE_INDEX,
    encode_sec_learn_params,
    encode_sec_reply_query_params,
    encode_sec_send_cmd_tel_params,
    encode_sec_storage_index_params,
    encode_sec_wr_userdata_params,
    validate_button_number,
    validate_storage_index,
)
from .models import (
    SecCommandTelegram,
    SecSendCmdTelRequest,
    SecSendCmdTelResponse,
    SecStorageEntry,
)
from .send import parse_sec_send_response
from .states import (
    SecwaveMovement,
    SecwavePosition,
    SecwavePrimaryState,
    SecwaveReplyState,
    encode_primary_state,
    encode_reply_state,
    parse_primary_state,
    parse_reply_state,
)
from .telegram import (
    parse_sec_delete_result_with_index,
    parse_sec_learn_result,
    parse_sec_rcv_result,
    parse_sec_stat_result,
    parse_sec_stat_result_with_index,
    parse_sec_storage_result,
    parse_sec_telegram,
)

__all__ = [
    "MAX_STORAGE_INDEX",
    "SecCommandTelegram",
    "SecLearnTelegramKind",
    "SecQuery",
    "SecSendCmdTelRequest",
    "SecSendCmdTelResponse",
    "SecStorageEntry",
    "SecTransmitterFlags",
    "SecwaveCommand",
    "SecwaveMovement",
    "SecwavePosition",
    "SecwavePrimaryState",
    "SecwaveReplyState",
    "encode_primary_state",
    "encode_reply_state",
    "encode_sec_learn_params",
    "encode_sec_reply_query_params",
    "encode_sec_send_cmd_tel_params",
    "encode_sec_storage_index_params",
    "encode_sec_wr_userdata_params",
    "parse_primary_state",
    "parse_reply_state",
    "parse_sec_delete_result_with_index",
    "parse_sec_learn_result",
    "parse_sec_rcv_result",
    "parse_sec_send_response",
    "parse_sec_stat_result",
    "parse_sec_stat_result_with_index",
    "parse_sec_storage_result",
    "parse_sec_telegram",
    "validate_button_number",
    "validate_storage_index",
]
