"""Transmitter battery warning state.

A low-battery indication is a push whose button byte is ``0x80``, followed
by a release. Neither telegram is a button press or a button release. The
real button, when one was pressed, is the earlier push/release pair.
Recovery stays ``low`` until ``recovery_count`` later pushes are not
low-battery.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable

from .events import ButtonPushEvent

BATTERY_OK = "ok"
BATTERY_LOW = "low"
EVENT_BATTERY_LOW = "battery_low"
EVENT_BATTERY_NORMAL = "battery_normal"
BATTERY_RECOVERY_COUNT = 2


@dataclass(frozen=True)
class TransmitterBatteryEvent:
    """Automation event emitted when the transmitter battery state changes."""

    event_type: str
    subtype: str
    state: str


BATTERY_EVENT_LOW = TransmitterBatteryEvent(EVENT_BATTERY_LOW, BATTERY_LOW, BATTERY_LOW)
BATTERY_EVENT_NORMAL = TransmitterBatteryEvent(
    EVENT_BATTERY_NORMAL, BATTERY_OK, BATTERY_OK
)


@dataclass
class _Record:
    state: str
    ok_streak: int = 0


class TransmitterBatteryTracker:
    """Per-transmitter battery state with delayed recovery.

    Keys are caller-defined (a serial or a device id). ``observe`` returns
    ``BATTERY_EVENT_LOW`` or ``BATTERY_EVENT_NORMAL`` only when the state changes.
    The first non-low telegram before any warning stores ``ok`` and returns
    ``None``. A warning that is already ``low`` does not transition again.
    Repeated telegrams that do not change the state do not rewrite it.
    """

    def __init__(self, recovery_count: int = BATTERY_RECOVERY_COUNT) -> None:
        if recovery_count < 1:
            raise ValueError("recovery_count must be at least 1")
        self._recovery_count = recovery_count
        self._items: dict[Hashable, _Record] = {}
        self._low_battery_release: set[Hashable] = set()

    def state_of(self, key: Hashable) -> str | None:
        """Return ``ok``, ``low``, or ``None`` when nothing was seen yet."""
        record = self._items.get(key)
        if record is None:
            return None
        return record.state

    def seed(self, key: Hashable, state: str) -> None:
        """Remember a restored state. A live state is left unchanged."""
        if state not in (BATTERY_OK, BATTERY_LOW) or key in self._items:
            return
        self._items[key] = _Record(state)

    def observe_push(
        self, key: Hashable, event: ButtonPushEvent
    ) -> TransmitterBatteryEvent | None:
        """Apply one push. Learn-control telegrams leave the battery state unchanged.

        A ``0x80`` push arms the following release: that release closes the
        low-battery pair and is not a button release.
        """
        if not event.is_low_battery and not event.is_button_press:
            return None
        if event.is_low_battery:
            self._low_battery_release.add(key)
        else:
            self._low_battery_release.discard(key)
        return self.observe(key, low_battery=event.is_low_battery)

    def take_low_battery_release(self, key: Hashable) -> bool:
        """Return True when this release belongs to a preceding ``0x80`` push."""
        if key not in self._low_battery_release:
            return False
        self._low_battery_release.remove(key)
        return True

    def observe(
        self, key: Hashable, *, low_battery: bool
    ) -> TransmitterBatteryEvent | None:
        """Apply a classified push. Return the library event on a transition."""
        record = self._items.get(key)
        if low_battery:
            if record is None:
                self._items[key] = _Record(BATTERY_LOW)
                return BATTERY_EVENT_LOW
            if record.ok_streak:
                record.ok_streak = 0
            if record.state == BATTERY_LOW:
                return None
            record.state = BATTERY_LOW
            return BATTERY_EVENT_LOW

        if record is None:
            self._items[key] = _Record(BATTERY_OK)
            return None
        if record.state != BATTERY_LOW:
            return None

        record.ok_streak += 1
        if record.ok_streak < self._recovery_count:
            return None
        record.state = BATTERY_OK
        record.ok_streak = 0
        return BATTERY_EVENT_NORMAL
