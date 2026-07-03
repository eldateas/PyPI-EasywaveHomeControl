"""Easywave sensor payload parsing (Spec Table 5 and 6)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Union

from .common import TimerDuration, get_bits
from .exceptions import InvalidPayloadError


class MeasurementType(IntEnum):
    TEMPERATURE = 4
    HUMIDITY = 5


@dataclass(frozen=True)
class SensorLearnPayload:
    version: int
    has_battery: bool
    battery_level: int
    capabilities: int

    @property
    def measures_temperature(self) -> bool:
        return bool((self.capabilities >> 4) & 1)

    @property
    def measures_humidity(self) -> bool:
        return bool((self.capabilities >> 5) & 1)


@dataclass(frozen=True)
class SensorMeasurementPayload:
    version: int
    has_battery: bool
    battery_level: int
    measurement_type: MeasurementType
    has_reference: bool
    raw_value: int
    reference_value: int
    max_interval: TimerDuration

    @property
    def temperature_celsius(self) -> float | None:
        if self.measurement_type != MeasurementType.TEMPERATURE:
            return None
        return self.raw_value / 10.0

    @property
    def humidity_percent(self) -> float | None:
        if self.measurement_type != MeasurementType.HUMIDITY:
            return None
        return self.raw_value / 10.0

    @property
    def reference_temperature_celsius(self) -> float | None:
        if not self.has_reference or self.measurement_type != MeasurementType.TEMPERATURE:
            return None
        return self.reference_value / 10.0

    @property
    def reference_humidity_percent(self) -> float | None:
        if not self.has_reference or self.measurement_type != MeasurementType.HUMIDITY:
            return None
        return self.reference_value / 10.0


SensorPayload = Union[SensorLearnPayload, SensorMeasurementPayload]


def parse_sensor_payload(info_data: bytes) -> SensorPayload:
    """Parse 8-byte sensor payload from EW_RCV_EX or EWB_RCV."""
    if len(info_data) < 8:
        raise InvalidPayloadError(f"Sensor payload must be 8 bytes, got {len(info_data)}")

    version = info_data[0] & 0x07
    if version != 0:
        raise InvalidPayloadError(f"Unsupported sensor payload version {version}")

    flags = info_data[1]
    has_battery = bool(flags & 0x40)
    battery_level = get_bits(flags, 5, 3)
    is_learn = bool(flags & 0x80)

    if is_learn:
        capabilities = int.from_bytes(info_data[2:8], "big")
        return SensorLearnPayload(
            version=version,
            has_battery=has_battery,
            battery_level=battery_level,
            capabilities=capabilities,
        )

    measurement_raw = info_data[2]
    measurement_type_value = get_bits(measurement_raw, 7, 2)
    try:
        measurement_type = MeasurementType(measurement_type_value)
    except ValueError as exc:
        raise InvalidPayloadError(
            f"Unsupported sensor measurement type {measurement_type_value}"
        ) from exc

    has_reference = bool(measurement_raw & 0x01)
    raw_value = int.from_bytes(info_data[3:5], "big")
    reference_value = int.from_bytes(info_data[5:7], "big")
    interval_byte = info_data[7]
    max_interval = TimerDuration(
        mantissa=get_bits(interval_byte, 3, 0),
        exponent=get_bits(interval_byte, 7, 4),
        factor_minutes=15.0,
    )

    return SensorMeasurementPayload(
        version=version,
        has_battery=has_battery,
        battery_level=battery_level,
        measurement_type=measurement_type,
        has_reference=has_reference,
        raw_value=raw_value,
        reference_value=reference_value,
        max_interval=max_interval,
    )
