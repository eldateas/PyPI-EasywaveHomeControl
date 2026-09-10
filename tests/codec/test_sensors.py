from __future__ import annotations

import pytest

from easywave_home_control.codec import (
    MeasurementType,
    SensorPayloadFormat,
    parse_sensor_payload,
)
from easywave_home_control.codec.sensors import (
    BatteryLevel,
    SensorLearnPayload,
    SensorMeasurementPayload,
)

# Live EasywavePlusDaten SENSOR_DATA (info_type 0x02) payloads after type byte.
LIVE_TEMP = bytes([0x80, 0x78, 0x12, 0x17, 0x3B, 0x00, 0x00, 0x35])
LIVE_HUMIDITY = bytes([0x80, 0x78, 0x16, 0x0A, 0x31, 0x00, 0x00, 0x35])


def test_table6_live_temperature_telegram() -> None:
    """Wire type 4, raw 5947 → 24.20 °C (n/20 K − 273.15)."""
    payload = parse_sensor_payload(LIVE_TEMP)
    assert isinstance(payload, SensorMeasurementPayload)
    assert payload.wire_measurement_type == 4
    assert payload.measurement_type == MeasurementType.TEMPERATURE
    assert payload.payload_format == SensorPayloadFormat.TABLE6
    assert payload.has_battery
    assert payload.battery_level == BatteryLevel.FULL
    assert payload.raw_value == 5947
    assert payload.temperature_kelvin == pytest.approx(297.35)
    assert payload.temperature_celsius == pytest.approx(24.20)
    assert payload.humidity_percent is None


def test_table6_live_humidity_telegram() -> None:
    """Wire type 5, raw 2609 → ~63.71 % (100·n/4095)."""
    payload = parse_sensor_payload(LIVE_HUMIDITY)
    assert isinstance(payload, SensorMeasurementPayload)
    assert payload.wire_measurement_type == 5
    assert payload.measurement_type == MeasurementType.HUMIDITY
    assert payload.raw_value == 2609
    assert payload.humidity_percent == pytest.approx(100.0 * 2609 / 4095)
    assert payload.temperature_celsius is None


def test_table6_humidity_full_scale() -> None:
    payload = parse_sensor_payload(bytes([0x00, 0x40, 0x14, 0x0F, 0xFF, 0x00, 0x00, 0x00]))
    assert isinstance(payload, SensorMeasurementPayload)
    assert payload.measurement_type == MeasurementType.HUMIDITY
    assert payload.humidity_percent == pytest.approx(100.0)


def test_measurement_type_matches_table6_wire_codes() -> None:
    assert MeasurementType.TEMPERATURE == 4
    assert MeasurementType.HUMIDITY == 5


def test_deprecated_format_aliases_still_use_table6() -> None:
    """NEO / LEGACY_RX21 aliases must not revive /100 scaling."""
    neo = parse_sensor_payload(LIVE_TEMP, payload_format=SensorPayloadFormat.NEO)
    legacy = parse_sensor_payload(
        LIVE_TEMP, payload_format=SensorPayloadFormat.LEGACY_RX21
    )
    assert isinstance(neo, SensorMeasurementPayload)
    assert isinstance(legacy, SensorMeasurementPayload)
    assert neo.temperature_celsius == pytest.approx(24.20)
    assert legacy.temperature_celsius == pytest.approx(24.20)


def test_sth01_learn_capabilities_temperature_and_humidity() -> None:
    """Learn telegram: capability bits 4 (temp) and 5 (humidity)."""
    caps = (1 << 4) | (1 << 5)
    payload = parse_sensor_payload(
        bytes([0x00, 0xF8, 0x00, 0x00, 0x00, 0x00, 0x00, caps & 0xFF])
    )
    assert isinstance(payload, SensorLearnPayload)
    assert payload.measures_temperature
    assert payload.measures_humidity
    assert payload.supported_measurement_types == (
        MeasurementType.TEMPERATURE,
        MeasurementType.HUMIDITY,
    )
    assert payload.battery_is_full
    assert not payload.battery_is_weak


def test_learn_temperature_only() -> None:
    payload = parse_sensor_payload(
        bytes([0x00, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 1 << 4])
    )
    assert isinstance(payload, SensorLearnPayload)
    assert payload.measures_temperature
    assert not payload.measures_humidity
    assert payload.supported_measurement_types == (MeasurementType.TEMPERATURE,)


def test_learn_humidity_only() -> None:
    payload = parse_sensor_payload(
        bytes([0x00, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 1 << 5])
    )
    assert isinstance(payload, SensorLearnPayload)
    assert not payload.measures_temperature
    assert payload.measures_humidity


def test_measurement_battery_weak() -> None:
    payload = parse_sensor_payload(bytes([0x00, 0x40, 0x10, 0x16, 0xE7, 0x00, 0x00, 0x00]))
    assert isinstance(payload, SensorMeasurementPayload)
    assert payload.has_battery
    assert payload.battery_level == BatteryLevel.WEAK
    assert payload.battery_is_weak


def test_measurement_should_ignore_bit() -> None:
    """Table 6 bit 1 on measurement type byte."""
    payload = parse_sensor_payload(LIVE_TEMP)
    assert isinstance(payload, SensorMeasurementPayload)
    assert payload.should_ignore


def test_measurement_with_reference_value() -> None:
    """Bit 0 set: reference uses same Table 6 scale (25 °C → raw 5963)."""
    payload = parse_sensor_payload(bytes([0x00, 0x40, 0x11, 0x16, 0xE7, 0x17, 0x4B, 0x00]))
    assert isinstance(payload, SensorMeasurementPayload)
    assert payload.has_reference
    assert payload.reference_value == 5963
    assert payload.reference_temperature_celsius == pytest.approx(25.0)
