"""Easywave sensor payload parsing (RX Spec Table 5 and 6).

``EWB_RCV`` / ``EW_RCV_EX`` with ``info_type`` ``TM_IT_SENSOR_DATA`` (0x02) carry an
8-byte measurement/learn payload. Layout and scaling follow **Table 6** for all
RxModule gateways (RX11, RX21, RX22, RX25).

Other ELDAT products such as ST01, SH01, SL01, or RTS40 use classic Easywave
button telegrams and are **not** parsed by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Union

from .common import TimerDuration, get_bits
from .exceptions import InvalidPayloadError


class SensorPayloadFormat(IntEnum):
    """Kept for API compatibility; all values use Table 6 (the only valid encoding)."""

    TABLE6 = 0
    """RX Spec Table 6 (default)."""

    NEO = 0
    """Deprecated alias of ``TABLE6``."""

    LEGACY_RX21 = 1
    """Deprecated alias of ``TABLE6`` (same formulas)."""


class MeasurementType(IntEnum):
    """Measurement type codes from Table 6 (offset 2, bits 7–2)."""

    TEMPERATURE = 4
    HUMIDITY = 5


class BatteryLevel(IntEnum):
    """Battery level from learn/measurement flags (Spec: only 0 and 7 are used)."""

    WEAK = 0
    FULL = 7


_TEMP_RAW_PER_KELVIN = 20.0
_KELVIN_ZERO_CELSIUS = 273.15
_HUMIDITY_FULL_SCALE = 4095.0


def _temperature_celsius(raw_value: int) -> float:
    """Table 6: ``T = n/20`` Kelvin → Celsius."""
    return raw_value / _TEMP_RAW_PER_KELVIN - _KELVIN_ZERO_CELSIUS


def _humidity_percent(raw_value: int) -> float:
    """Table 6: ``φ = 100 · n / 4095`` percent, rounded to 1 decimal place."""
    return round(100.0 * raw_value / _HUMIDITY_FULL_SCALE, 1)


@dataclass(frozen=True)
class SensorLearnPayload:
    version: int
    has_battery: bool
    battery_level: int
    capabilities: int

    @property
    def measures_temperature(self) -> bool:
        """Capability bit 4 (Spec Table 5)."""
        return bool((self.capabilities >> 4) & 1)

    @property
    def measures_humidity(self) -> bool:
        """Capability bit 5 (Spec Table 5)."""
        return bool((self.capabilities >> 5) & 1)

    @property
    def supported_measurement_types(self) -> tuple[MeasurementType, ...]:
        types: list[MeasurementType] = []
        if self.measures_temperature:
            types.append(MeasurementType.TEMPERATURE)
        if self.measures_humidity:
            types.append(MeasurementType.HUMIDITY)
        return tuple(types)

    @property
    def battery_is_weak(self) -> bool:
        return self.has_battery and self.battery_level == BatteryLevel.WEAK

    @property
    def battery_is_full(self) -> bool:
        return self.has_battery and self.battery_level == BatteryLevel.FULL


@dataclass(frozen=True)
class SensorMeasurementPayload:
    version: int
    has_battery: bool
    battery_level: int
    wire_measurement_type: int
    measurement_type: MeasurementType | int
    payload_format: SensorPayloadFormat
    should_ignore: bool
    has_reference: bool
    raw_value: int
    reference_value: int
    max_interval: TimerDuration

    @property
    def temperature_celsius(self) -> float | None:
        if self.measurement_type != MeasurementType.TEMPERATURE:
            return None
        return _temperature_celsius(self.raw_value)

    @property
    def temperature_kelvin(self) -> float | None:
        """Table 6: ``n / 20`` Kelvin."""
        if self.measurement_type != MeasurementType.TEMPERATURE:
            return None
        return self.raw_value / _TEMP_RAW_PER_KELVIN

    @property
    def humidity_percent(self) -> float | None:
        if self.measurement_type != MeasurementType.HUMIDITY:
            return None
        return _humidity_percent(self.raw_value)

    @property
    def reference_temperature_celsius(self) -> float | None:
        if not self.has_reference or self.measurement_type != MeasurementType.TEMPERATURE:
            return None
        return _temperature_celsius(self.reference_value)

    @property
    def reference_humidity_percent(self) -> float | None:
        if not self.has_reference or self.measurement_type != MeasurementType.HUMIDITY:
            return None
        return _humidity_percent(self.reference_value)

    @property
    def battery_is_weak(self) -> bool:
        return self.has_battery and self.battery_level == BatteryLevel.WEAK


SensorPayload = Union[SensorLearnPayload, SensorMeasurementPayload]


def parse_sensor_payload(
    info_data: bytes,
    *,
    payload_format: SensorPayloadFormat = SensorPayloadFormat.TABLE6,
) -> SensorPayload:
    """Parse 8-byte sensor payload from EW_RCV_EX or EWB_RCV (Table 6).

    ``payload_format`` is ignored for scaling/types (always Table 6); retained for
    call-site compatibility.
    """
    del payload_format  # only Table 6 is valid
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
    wire_measurement_type = get_bits(measurement_raw, 7, 2)
    if wire_measurement_type not in (
        MeasurementType.TEMPERATURE,
        MeasurementType.HUMIDITY,
    ):
        raise InvalidPayloadError(
            f"Unsupported sensor measurement type {wire_measurement_type}"
        )

    try:
        measurement_type = MeasurementType(wire_measurement_type)
    except ValueError:
        measurement_type = wire_measurement_type

    should_ignore = bool(measurement_raw & 0x02)
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
        wire_measurement_type=wire_measurement_type,
        measurement_type=measurement_type,
        payload_format=SensorPayloadFormat.TABLE6,
        should_ignore=should_ignore,
        has_reference=has_reference,
        raw_value=raw_value,
        reference_value=reference_value,
        max_interval=max_interval,
    )
