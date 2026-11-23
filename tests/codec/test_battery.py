from easywave_home_control.codec import (
    BATTERY_EVENT_LOW,
    BATTERY_EVENT_NORMAL,
    BATTERY_LOW,
    BATTERY_OK,
    ButtonFunction,
    ButtonPushEvent,
    EasywaveButton,
    TransmitterBatteryTracker,
    parse_ewb_rcv,
)
from easywave_home_control.protocols.rx11_rx2x.protocol import InfoType


def test_low_battery_byte_is_not_a_button_press() -> None:
    event = parse_ewb_rcv(InfoType.TM_IT_EASW_PUSH, b"\x01" * 16, bytes([0x80]))
    assert isinstance(event, ButtonPushEvent)
    assert event.button == EasywaveButton.A
    assert event.function == ButtonFunction.LOW_BATTERY
    assert event.should_ignore is False
    assert event.is_low_battery is True
    assert event.is_button_press is False


def test_default_button_is_a_press() -> None:
    event = ButtonPushEvent(
        transmitter_serial=b"\x01" * 16,
        button=EasywaveButton.B,
        function=ButtonFunction.DEFAULT,
        should_ignore=False,
    )
    assert event.is_low_battery is False
    assert event.is_button_press is True


def test_recovery_needs_two_ok_telegrams() -> None:
    tracker = TransmitterBatteryTracker()
    serial = b"\x02" * 16

    assert tracker.observe(serial, low_battery=False) is None
    assert tracker.state_of(serial) == BATTERY_OK

    assert tracker.observe(serial, low_battery=True) == BATTERY_EVENT_LOW
    assert tracker.observe(serial, low_battery=True) is None
    assert tracker.state_of(serial) == BATTERY_LOW

    assert tracker.observe(serial, low_battery=False) is None
    assert tracker.state_of(serial) == BATTERY_LOW
    assert tracker.observe(serial, low_battery=False) == BATTERY_EVENT_NORMAL
    assert tracker.state_of(serial) == BATTERY_OK


def test_low_telegram_resets_recovery_streak() -> None:
    tracker = TransmitterBatteryTracker()
    key = "tx"
    tracker.observe(key, low_battery=True)
    tracker.observe(key, low_battery=False)
    assert tracker.observe(key, low_battery=True) is None
    assert tracker.observe(key, low_battery=False) is None
    noticed = tracker.observe(key, low_battery=False)
    assert noticed == BATTERY_EVENT_NORMAL
    assert noticed is not None
    assert noticed.event_type == "battery_normal"
    assert noticed.subtype == "ok"


def test_low_battery_pair_marks_only_the_following_release() -> None:
    tracker = TransmitterBatteryTracker()
    press = ButtonPushEvent(
        transmitter_serial=b"\x01" * 16,
        button=EasywaveButton.A,
        function=ButtonFunction.DEFAULT,
        should_ignore=False,
    )
    warning = ButtonPushEvent(
        transmitter_serial=b"\x01" * 16,
        button=EasywaveButton.A,
        function=ButtonFunction.LOW_BATTERY,
        should_ignore=False,
    )
    assert tracker.take_low_battery_release("tx") is False
    assert tracker.observe_push("tx", press) is None
    assert tracker.take_low_battery_release("tx") is False
    assert tracker.observe_push("tx", warning) == BATTERY_EVENT_LOW
    assert tracker.take_low_battery_release("tx") is True
    assert tracker.take_low_battery_release("tx") is False


def test_learn_control_telegram_does_not_change_battery() -> None:
    tracker = TransmitterBatteryTracker()
    warning = ButtonPushEvent(
        transmitter_serial=b"\x01" * 16,
        button=EasywaveButton.A,
        function=ButtonFunction.LOW_BATTERY,
        should_ignore=False,
    )
    learn = ButtonPushEvent(
        transmitter_serial=b"\x01" * 16,
        button=EasywaveButton.A,
        function=ButtonFunction.REMOTE_LEARN_ADD,
        should_ignore=True,
    )
    assert tracker.observe_push("tx", warning) == BATTERY_EVENT_LOW
    assert tracker.observe_push("tx", learn) is None
    assert tracker.observe_push("tx", learn) is None
    assert tracker.state_of("tx") == BATTERY_LOW


def test_seed_does_not_overwrite_live_state() -> None:
    tracker = TransmitterBatteryTracker()
    tracker.observe("tx1", low_battery=True)
    tracker.seed("tx1", BATTERY_OK)
    assert tracker.state_of("tx1") == BATTERY_LOW
    tracker.seed("tx2", BATTERY_OK)
    assert tracker.state_of("tx2") == BATTERY_OK
    tracker.seed("tx3", "full")
    assert tracker.state_of("tx3") is None
