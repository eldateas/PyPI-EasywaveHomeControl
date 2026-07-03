from __future__ import annotations

import pytest

from easywave_home_control.codec import secwave
from easywave_home_control.codec.exceptions import InvalidPayloadError


def test_parse_sec_rcv_open_command() -> None:
    result = (
        0,
        5,
        0x01,
        int(secwave.SecwaveCommand.OPEN),
        0x12345678,
        0x80,
        0,
    )
    error_code, telegram = secwave.parse_sec_rcv_result(result)
    assert error_code == 0
    assert telegram is not None
    assert telegram.storage_index == 5
    assert telegram.query.wants_reply is True
    assert telegram.fixed_command == secwave.SecwaveCommand.OPEN
    assert telegram.user_data == 0x12345678
    assert telegram.flags.mobile is True
    assert telegram.learn_kind == secwave.SecLearnTelegramKind.NORMAL


def test_parse_sec_learn_result_includes_storage_index() -> None:
    result = (
        0,
        42,
        0x00,
        0,
        0xDEADBEEF,
        0x00,
        int(secwave.SecLearnTelegramKind.NEW_LEARN_IN_PROGRESS),
    )
    error_code, telegram = secwave.parse_sec_learn_result(result)
    assert error_code == 0
    assert telegram is not None
    assert telegram.storage_index == 42
    assert telegram.learn_kind == secwave.SecLearnTelegramKind.NEW_LEARN_IN_PROGRESS


def test_parse_primary_state_table8_bits() -> None:
    # position=7 (END_OPENED), opening=1 (bit 6), movement=1 (bits 7-8), vacation off=1 (bit 11)
    word = (7 & 0x07) | (1 << 6) | (1 << 7) | (1 << 11)
    parsed = secwave.parse_primary_state(word)
    assert parsed.position == secwave.SecwavePosition.END_OPENED
    assert parsed.opening is True
    assert parsed.movement == secwave.SecwaveMovement.MOVING
    assert parsed.vacation_mode_off is True
    assert parsed.vacation_mode_on is False


def test_parse_primary_state_reserved_bits_ignored() -> None:
    word = 0xF000 | (4 & 0x07)  # reserved bits set, position END_CLOSED
    parsed = secwave.parse_primary_state(word)
    assert parsed.position == secwave.SecwavePosition.END_CLOSED


def test_parse_sec_learn_kind_invalid_passthrough() -> None:
    result = (0, 1, 0, 0, 0, 0, 99)
    _, telegram = secwave.parse_sec_rcv_result(result)
    assert telegram is not None
    assert telegram.learn_kind == 99

def test_parse_primary_state_roundtrip() -> None:
    state = secwave.SecwavePrimaryState(
        position=secwave.SecwavePosition.END_OPENED,
        opening=True,
        movement=secwave.SecwaveMovement.MOVING,
        vacation_mode_off=True,
    )
    word = secwave.encode_primary_state(state)
    parsed = secwave.parse_primary_state(word)
    assert parsed.position == state.position
    assert parsed.opening == state.opening
    assert parsed.movement == state.movement
    assert parsed.vacation_mode_off == state.vacation_mode_off
    assert word & 0x0800 == 0x0800  # only known bits set besides position/movement/opening


def test_encode_sec_learn_params() -> None:
    assert secwave.encode_sec_learn_params(0x12345678) == bytes([0x12, 0x34, 0x56, 0x78])


def test_encode_sec_storage_index_params() -> None:
    assert secwave.encode_sec_storage_index_params(127) == bytes([0, 127])
    with pytest.raises(InvalidPayloadError):
        secwave.encode_sec_storage_index_params(128)


def test_encode_sec_wr_userdata_params() -> None:
    params = secwave.encode_sec_wr_userdata_params(5, 0xAABBCCDD)
    assert params == bytes([0, 5, 0xAA, 0xBB, 0xCC, 0xDD])


@pytest.mark.parametrize(
    ("command", "expected_bytes"),
    [
        (secwave.SecwaveCommand.CLOSE, bytes([0, 8])),
        (secwave.SecwaveCommand.OPEN, bytes([0, 16])),
        (secwave.SecwaveCommand.HALT, bytes([0, 24])),
        (secwave.SecwaveCommand.PULSE_INTERMEDIATE_CLOSED, bytes([0, 32])),
        (secwave.SecwaveCommand.PULSE_INTERMEDIATE_OPENED, bytes([0, 33])),
        (secwave.SecwaveCommand.PULSE, bytes([0, 56])),
        (secwave.SecwaveCommand.LIGHT, bytes([0, 66])),
        (secwave.SecwaveCommand.LIGHT_TIMER, bytes([0, 67])),
        (secwave.SecwaveCommand.VACATION_MODE, bytes([0, 74])),
    ],
)
def test_secwave_command_codes_table7(command: secwave.SecwaveCommand, expected_bytes: bytes) -> None:
    request = secwave.SecSendCmdTelRequest(
        button_number=0,
        query=secwave.SecQuery(wants_reply=False, reply_only=False),
        command=int(command),
        flags=secwave.SecTransmitterFlags(low_battery=False, mobile=False),
    )
    params = secwave.encode_sec_send_cmd_tel_params(request)
    assert params[3:5] == expected_bytes


def test_encode_send_cmd_tel_params() -> None:
    request = secwave.SecSendCmdTelRequest(
        button_number=3,
        query=secwave.SecQuery(wants_reply=True, reply_only=False),
        command=int(secwave.SecwaveCommand.CLOSE),
        flags=secwave.SecTransmitterFlags(low_battery=False, mobile=True),
    )
    params = secwave.encode_sec_send_cmd_tel_params(request)
    assert params == bytes([0, 3, 0x01, 0, 8, 0x80])


def test_encode_reply_query_params() -> None:
    reply = secwave.SecwaveReplyState(
        primary=secwave.SecwavePrimaryState(
            position=secwave.SecwavePosition.END_CLOSED,
            opening=False,
            movement=secwave.SecwaveMovement.STOPPED,
            vacation_mode_off=True,
        )
    )
    params = secwave.encode_sec_reply_query_params(reply)
    primary, secondary = secwave.encode_reply_state(reply)
    assert params == bytes([(primary >> 8) & 0xFF, primary & 0xFF, 0, 0])


def test_parse_sec_send_response() -> None:
    response = secwave.parse_sec_send_response(0, 0)
    assert response.reply is None

    response = secwave.parse_sec_send_response(0, 0, queried_reply=False)
    assert response.reply is None

    primary = secwave.encode_primary_state(
        secwave.SecwavePrimaryState(
            position=secwave.SecwavePosition.LOWER_INTERMEDIATE,
            opening=False,
            movement=secwave.SecwaveMovement.STOPPED,
            vacation_mode_off=True,
        )
    )
    response = secwave.parse_sec_send_response(primary, 0)
    assert response.reply is not None
    assert response.reply.primary.position == secwave.SecwavePosition.LOWER_INTERMEDIATE


def test_parse_sec_stat_with_index() -> None:
    error_code, entry = secwave.parse_sec_stat_result_with_index(12, (0, True, 0xAABBCCDD))
    assert error_code == 0
    assert entry is not None
    assert entry.storage_index == 12
    assert entry.is_used is True
    assert entry.user_data == 0xAABBCCDD


def test_parse_sec_delete_result_with_index() -> None:
    error_code, entry = secwave.parse_sec_delete_result_with_index(3, (0, False, 0))
    assert error_code == 0
    assert entry is not None
    assert entry.storage_index == 3
    assert entry.is_used is False
    assert entry.user_data == 0
