from __future__ import annotations

import struct

import pytest

from easywave_home_control.codec import easywave, parse_ew_rcv_ex_result
from easywave_home_control.codec.events import ButtonFunction, EasywaveButton
from easywave_home_control.protocols.rx09.parsing import (
    parse_bootloader_response,
    parse_button_response,
    parse_echo_response,
    parse_getp_response,
    parse_id_response,
    parse_led_response,
    parse_rdp_response,
    parse_rec_message,
)
from easywave_home_control.protocols.rx11_rx2x.protocol import (
    ErrorCode,
    FunctionCode,
    ICP,
    InfoType,
    parse_icp_data,
)


def test_encode_send_button_byte_spec_table() -> None:
    assert easywave.encode_send_button_byte(easywave.EasywaveSendButton.A) == 0x00
    assert easywave.encode_send_button_byte(easywave.EasywaveSendButton.B) == 0x01
    assert (
        easywave.encode_send_button_byte(
            easywave.EasywaveSendButton.C,
            function=ButtonFunction.EMULATED_HOLD,
        )
        == 0x16
    )
    assert easywave.encode_send_button_byte(
        easywave.EasywaveSendButton.A, function=ButtonFunction.LOW_BATTERY
    ) == 0x80


def test_parse_button_info_byte_remote_learn() -> None:
    button, function, ignore = easywave.parse_button_info_byte(0x08)
    assert button == EasywaveButton.A
    assert function == ButtonFunction.REMOTE_LEARN_ADD
    assert ignore is True


def test_parse_ew_rcv_ex_result_button_push() -> None:
    result = (0, int(InfoType.TM_IT_EASW_PUSH), b"\x01" * 16, bytes([0x00]))
    error_code, event = parse_ew_rcv_ex_result(result)
    assert error_code == 0
    assert event is not None
    assert event.button == EasywaveButton.A


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ("ID,1234,5678,0001", (0x1234, 0x5678, 0x0001)),
        ("ERROR", None),
        ("ID,zz,5678,0001", None),
    ],
)
def test_rx09_parse_id_response(response: str, expected: tuple[int, int, int] | None) -> None:
    assert parse_id_response(response) == expected


def test_rx09_parse_getp_response() -> None:
    assert parse_getp_response("GETP,40") == 0x40
    assert parse_getp_response("GETP?,40") is None


def test_rx09_parse_rdp_response() -> None:
    assert parse_rdp_response("RDP,05,00123456", expected_position=5) == 0x123456
    assert parse_rdp_response("RDP,06,00123456", expected_position=5) is None


def test_rx09_parse_rec_message() -> None:
    assert parse_rec_message("REC,00123456,A") == (0x123456, "A")
    assert parse_rec_message("REC,00123456,X") is None


def test_rx09_status_strings() -> None:
    assert parse_echo_response("Echo is ON") is True
    assert parse_echo_response("Echo is OFF") is False
    assert parse_echo_response("Echo is OFF but ON substring") is None
    assert parse_led_response("Led is ON") is True
    assert parse_button_response("Button is pressed") is True
    assert parse_bootloader_response("Bootloader is starting now !") is True


def _icp_data(*fields: bytes) -> bytes:
    return b"".join(fields)


def test_parse_icp_ewb_join_device() -> None:
    serial = b"\x11" * 16
    icp = ICP(handle=0, result=ErrorCode.SUCCESS, data=serial + bytes([0x05]))
    parsed = parse_icp_data(icp, FunctionCode.EWB_JOIN_DEVICE)
    assert parsed["receiver"] == serial
    assert parsed["device_type"] == 0x05


def test_parse_icp_ewb_change_state() -> None:
    icp = ICP(handle=0, result=ErrorCode.SUCCESS, data=bytes([2]) + b"\xAA\xBB\xCC\xDD")
    parsed = parse_icp_data(icp, FunctionCode.EWB_CHANGE_STATE)
    assert parsed["mode"] == 2
    assert parsed["state"] == b"\xAA\xBB\xCC\xDD"


def test_parse_icp_ew_rcv_ex_sensor() -> None:
    serial = b"\x22" * 16
    sensor = b"\x00\x80" + b"\x00" * 6
    icp = ICP(
        handle=0,
        result=ErrorCode.SUCCESS,
        data=bytes([InfoType.TM_IT_SENSOR_DATA]) + serial + sensor,
    )
    parsed = parse_icp_data(icp, FunctionCode.EW_RCV_EX)
    assert parsed["info_type"] == InfoType.TM_IT_SENSOR_DATA
    assert parsed["receiver_or_transmitter"] == serial
    assert parsed["info_data"] == sensor


def test_parse_icp_sec_send_reply() -> None:
    icp = ICP(
        handle=0,
        result=ErrorCode.SUCCESS,
        data=struct.pack(">HH", 0x0804, 0),
    )
    parsed = parse_icp_data(icp, FunctionCode.SEC_SEND_CMD_TEL)
    assert parsed["primary_state"] == 0x0804
    assert parsed["secondary_state"] == 0


def test_protocol_expected_icp_payload_sizes() -> None:
    """Document spec ICP payload sizes (handle+error+data)."""
    sizes = {
        FunctionCode.EW_RCV_BUTTON: 21,
        FunctionCode.EW_RCV_EX: 28,
        FunctionCode.EWB_RCV: 28,
        FunctionCode.EWB_JOIN_DEVICE: 20,
        FunctionCode.EWB_CHANGE_STATE: 8,
        FunctionCode.SEC_RCV: 14,
        FunctionCode.SEC_SEND_CMD_TEL: 7,
    }
    for function, expected in sizes.items():
        data_len = expected - 3
        icp = ICP(handle=0, result=ErrorCode.SUCCESS, data=b"\x00" * data_len)
        assert len(icp.data) == data_len, function
