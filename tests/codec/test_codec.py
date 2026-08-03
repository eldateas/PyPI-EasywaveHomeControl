from __future__ import annotations

import pytest

from easywave_home_control.codec import (
    ButtonFunction,
    EasywaveButton,
    MotorActivity,
    MotorCommand,
    MotorMoveCommand,
    StateDirection,
    SwitchChangeCommand,
    SwitchDesiredAction,
    SwitchOnOffState,
    SwitchPosition,
    encode_ewb_state,
    parse_ewb_rcv,
    parse_ewb_state,
)
from easywave_home_control.codec.common import TimerDuration, encode_state_word
from easywave_home_control.protocols.rx11_rx2x.protocol import DeviceType, InfoType


def test_switch_on_off_roundtrip_from_device() -> None:
    raw = encode_state_word((3 << 27) | (int(SwitchPosition.ON) << 24))
    state = parse_ewb_state(DeviceType.EWB_DT_SWITCH, 0, raw)
    assert isinstance(state, SwitchOnOffState)
    assert state.pulse_counter == 3
    assert state.position == SwitchPosition.ON
    assert encode_ewb_state(DeviceType.EWB_DT_SWITCH, 0, state, direction=StateDirection.FROM_DEVICE) == raw


def test_switch_change_command_to_device() -> None:
    command = SwitchChangeCommand(action=SwitchDesiredAction.ON)
    raw = encode_ewb_state(DeviceType.EWB_DT_SWITCH, 0, command)
    parsed = parse_ewb_state(DeviceType.EWB_DT_SWITCH, 0, raw, direction=StateDirection.TO_DEVICE)
    assert isinstance(parsed, SwitchChangeCommand)
    assert parsed.action == SwitchDesiredAction.ON


def test_parse_ewb_rcv_button_push() -> None:
    event = parse_ewb_rcv(
        InfoType.TM_IT_EASW_PUSH,
        b"\x01" * 16,
        bytes([0x08]),
    )
    assert event.button == EasywaveButton.A
    assert event.function == ButtonFunction.REMOTE_LEARN_ADD
    assert event.should_ignore is True


def test_parse_ewb_rcv_state_change() -> None:
    state_raw = encode_state_word((3 << 27) | (int(SwitchPosition.ON) << 24))
    info_data = bytes([0]) + state_raw
    event = parse_ewb_rcv(
        InfoType.TM_IT_EWBIDI_STATE,
        b"\x02" * 16,
        info_data,
        device_type=DeviceType.EWB_DT_SWITCH,
    )
    assert event.receiver_serial == b"\x02" * 16
    assert event.mode == 0
    assert isinstance(event.state, SwitchOnOffState)
    assert event.state.position == SwitchPosition.ON
    assert event.state.pulse_counter == 3


def test_motor_full_state_parse() -> None:
    word = (int(MotorActivity.STOPPED) << 25) | (50 << 17) | (1 << 7)
    raw = encode_state_word(word)
    state = parse_ewb_state(DeviceType.EWB_DT_MOTOR, 0, raw)
    assert state.activity == MotorActivity.STOPPED
    assert state.current_position == 50
    assert state.runtime_measured is True


def test_motor_move_command_encode() -> None:
    command = MotorMoveCommand(command=MotorCommand.STOP)
    raw = encode_ewb_state(DeviceType.EWB_DT_MOTOR, 0, command)
    parsed = parse_ewb_state(DeviceType.EWB_DT_MOTOR, 0, raw, direction=StateDirection.TO_DEVICE)
    assert isinstance(parsed, MotorMoveCommand)
    assert parsed.command == MotorCommand.STOP


def test_dual_motor_summary_reports_position() -> None:
    """Mode 0 FROM_DEVICE uses 0-100 in the activity field as position."""
    from easywave_home_control.codec.states import MultiMotorSummaryState

    # Channel 1 at protocol position 25, channel 2 opening to position.
    word = (25 << 25) | (int(MotorActivity.OPENING_TO_POSITION) << 17)
    raw = encode_state_word(word)
    state = parse_ewb_state(DeviceType.EWB_DT_DUAL_MOTOR, 0, raw)
    assert isinstance(state, MultiMotorSummaryState)
    assert state.channels[0].position == 25
    assert state.channels[0].activity == MotorActivity.STOPPED
    assert state.channels[1].position is None
    assert state.channels[1].activity == MotorActivity.OPENING_TO_POSITION


def test_quad_motor_summary_position_roundtrip() -> None:
    """Quad summary encode/decode preserves per-channel positions."""
    from easywave_home_control.codec.states import (
        MotorSummaryChannelState,
        MultiMotorSummaryState,
    )

    summary = MultiMotorSummaryState(
        channels=(
            MotorSummaryChannelState(1, MotorActivity.STOPPED, False, position=10),
            MotorSummaryChannelState(2, MotorActivity.STOPPED, False, position=40),
            MotorSummaryChannelState(3, MotorActivity.OPENING_RUNTIME, False),
            MotorSummaryChannelState(4, MotorActivity.STOPPED, False, position=100),
        )
    )
    raw = encode_ewb_state(
        DeviceType.EWB_DT_QUAD_MOTOR, 0, summary, direction=StateDirection.FROM_DEVICE
    )
    parsed = parse_ewb_state(DeviceType.EWB_DT_QUAD_MOTOR, 0, raw)
    assert isinstance(parsed, MultiMotorSummaryState)
    assert parsed.channels[0].position == 10
    assert parsed.channels[1].position == 40
    assert parsed.channels[2].position is None
    assert parsed.channels[2].activity == MotorActivity.OPENING_RUNTIME
    assert parsed.channels[3].position == 100


def test_timer_duration_minutes() -> None:
    duration = TimerDuration(mantissa=128, exponent=0)
    assert duration.total_minutes == pytest.approx(16.0)
    assert duration.total_seconds == pytest.approx(960.0)
