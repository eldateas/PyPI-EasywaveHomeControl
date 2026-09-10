"""Easywave sensor payload parsing (Spec Table 5 and 6).

DATA sensors (e.g. STH01 with ``1x DATA``) send 8-byte learn/measurement payloads via
``EW_RCV_EX`` / ``EWB_RCV``. Other ELDAT products such as ST01 (heating thermostat),
SH01 (humidity switch), SL01 (light sensor), or RTS40 (motion) use classic
Easywave button telegrams instead and are **not** parsed by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Union

from .common import TimerDuration, get_bits
from .exceptions import InvalidPayloadError


class SensorPayloadFormat(IntEnum):
    """How to interpret measurement type codes and raw value scaling."""

    NEO = 0
    """EWneo DATA sensors (STH01): wire type 4 = humidity, 5 = temperature, raw / 100.

    Verified against live STH01 telegrams (centi-°C / centi-% RH). Internal ADC
    formulas (e.g. Kelvin ``n/20`` or humidity ``100·n/4095``) do **not** apply to
    the air-interface payload field.
    """

    LEGACY_RX21 = 1
    """RX21 Table 6 legacy sensors: wire type 4 = temperature, 5 = humidity, raw / 10."""


class MeasurementType(IntEnum):
    """Semantic measurement unit (after format-specific wire-type mapping)."""

    HUMIDITY = 4
    TEMPERATURE = 5


class BatteryLevel(IntEnum):
    """Battery level from learn/measurement flags (Spec: only 0 and 7 are used)."""

    WEAK = 0
    FULL = 7


_NEO_VALUE_SCALE = 100.0
_LEGACY_VALUE_SCALE = 10.0


def _wire_to_semantic_type(
    wire_type: int, payload_format: SensorPayloadFormat
) -> MeasurementType | int:
    if payload_format == SensorPayloadFormat.NEO:
        try:
            return MeasurementType(wire_type)
        except ValueError:
            return wire_type
    if wire_type == 4:
        return MeasurementType.TEMPERATURE
    if wire_type == 5:
        return MeasurementType.HUMIDITY
    return wire_type


def _value_scale(payload_format: SensorPayloadFormat) -> float:
    return _LEGACY_VALUE_SCALE if payload_format == SensorPayloadFormat.LEGACY_RX21 else _NEO_VALUE_SCALE


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
        return self.raw_value / _value_scale(self.payload_format)

    @property
    def humidity_percent(self) -> float | None:
        if self.measurement_type != MeasurementType.HUMIDITY:
            return None
        return self.raw_value / _value_scale(self.payload_format)

    @property
    def reference_temperature_celsius(self) -> float | None:
        if not self.has_reference or self.measurement_type != MeasurementType.TEMPERATURE:
            return None
        return self.reference_value / _value_scale(self.payload_format)

    @property
    def reference_humidity_percent(self) -> float | None:
        if not self.has_reference or self.measurement_type != MeasurementType.HUMIDITY:
            return None
        return self.reference_value / _value_scale(self.payload_format)

    @property
    def battery_is_weak(self) -> bool:
        return self.has_battery and self.battery_level == BatteryLevel.WEAK


SensorPayload = Union[SensorLearnPayload, SensorMeasurementPayload]


def parse_sensor_payload(
    info_data: bytes,
    *,
    payload_format: SensorPayloadFormat = SensorPayloadFormat.NEO,
) -> SensorPayload:
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
    wire_measurement_type = get_bits(measurement_raw, 7, 2)
    if wire_measurement_type not in (4, 5) and payload_format == SensorPayloadFormat.NEO:
        raise InvalidPayloadError(
            f"Unsupported sensor measurement type {wire_measurement_type}"
        )

    measurement_type = _wire_to_semantic_type(wire_measurement_type, payload_format)
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
        payload_format=payload_format,
        should_ignore=should_ignore,
        has_reference=has_reference,
        raw_value=raw_value,
        reference_value=reference_value,
        max_interval=max_interval,
    )
