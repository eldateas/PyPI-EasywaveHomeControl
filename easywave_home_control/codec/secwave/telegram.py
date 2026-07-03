"""Parse Secwave SEC_RCV, SEC_LEARN, SEC_STAT, and SEC_DELETE telegrams."""

from __future__ import annotations

from .fields import SecLearnTelegramKind, SecQuery, SecTransmitterFlags
from .models import SecCommandTelegram, SecStorageEntry


def _learn_kind(value: int) -> SecLearnTelegramKind | int:
    try:
        return SecLearnTelegramKind(value)
    except ValueError:
        return value


def parse_sec_telegram(
    storage_index: int,
    sec_query: int,
    sec_cmd: int,
    user_data: int,
    sec_flags: int,
    lrn_tel: int,
) -> SecCommandTelegram:
    """Decode SEC_RCV / SEC_LEARN ICP fields (Spec offset 3-13)."""
    return SecCommandTelegram(
        storage_index=storage_index,
        query=SecQuery.from_byte(sec_query),
        command=sec_cmd,
        user_data=user_data,
        flags=SecTransmitterFlags.from_byte(sec_flags),
        learn_kind=_learn_kind(lrn_tel),
    )


def parse_sec_rcv_result(
    result: tuple[int, int, int, int, int, int, int],
) -> tuple[int, SecCommandTelegram | None]:
    """Parse the tuple returned by ``sec_rcv_request``."""
    error_code, stor_index, sec_query, sec_cmd, user_data, sec_flags, lrn_tel = result
    if error_code != 0:
        return error_code, None
    return error_code, parse_sec_telegram(
        stor_index, sec_query, sec_cmd, user_data, sec_flags, lrn_tel
    )


def parse_sec_learn_result(
    result: tuple[int, int, int, int, int, int, int],
) -> tuple[int, SecCommandTelegram | None]:
    """Parse the tuple returned by ``sec_learn_request``."""
    return parse_sec_rcv_result(result)


def parse_sec_storage_result(
    storage_index: int,
    result: tuple[int, bool, int],
) -> tuple[int, SecStorageEntry | None]:
    """Parse SEC_STAT or SEC_DELETE ICP (Spec offset 3-7)."""
    error_code, is_used, user_data = result
    if error_code != 0:
        return error_code, None
    return error_code, SecStorageEntry(
        storage_index=storage_index,
        is_used=is_used,
        user_data=user_data,
    )


def parse_sec_stat_result_with_index(
    storage_index: int, result: tuple[int, bool, int]
) -> tuple[int, SecStorageEntry | None]:
    return parse_sec_storage_result(storage_index, result)


def parse_sec_delete_result_with_index(
    storage_index: int, result: tuple[int, bool, int]
) -> tuple[int, SecStorageEntry | None]:
    return parse_sec_storage_result(storage_index, result)


def parse_sec_stat_result(result: tuple[int, bool, int]) -> tuple[int, SecStorageEntry | None]:
    """Parse ``sec_stat_request`` without storage index in the tuple."""
    error_code, entry = parse_sec_storage_result(0, result)
    return error_code, entry
