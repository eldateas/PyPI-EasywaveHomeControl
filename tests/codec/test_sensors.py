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


def test_neo_sth01_temperature_payload_bytes() -> None:
    """STH01: wire type 5, raw 2630 -> 26.30 °C (centi-degrees)."""
    payload = parse_sensor_payload(bytes([0x00, 0x40, 0x14, 0x0A, 0x46, 0x00, 0x00, 0x00]))
    assert isinstance(payload, SensorMeasurementPayload)
    assert payload.wire_measurement_type == 5
    assert payload.measurement_type == MeasurementType.TEMPERATURE
    assert payload.payload_format == SensorPayloadFormat.NEO
    assert payload.temperature_celsius == pytest.approx(26.3)
    assert payload.humidity_percent is None


def test_neo_sth01_humidity_payload_bytes() -> None:
    """STH01: wire type 4, raw 5942 -> 59.42 % (centi-percent)."""
    payload = parse_sensor_payload(bytes([0x00, 0x40, 0x10, 0x17, 0x36, 0x00, 0x00, 0x00]))
    assert isinstance(payload, SensorMeasurementPayload)
    assert payload.wire_measurement_type == 4
    assert payload.measurement_type == MeasurementType.HUMIDITY
    assert payload.humidity_percent == pytest.approx(59.42)
    assert payload.temperature_celsius is None


def test_measurement_type_wire_values() -> None:
    assert MeasurementType.HUMIDITY == 4
    assert MeasurementType.TEMPERATURE == 5


def test_sth01_learn_capabilities_temperature_and_humidity() -> None:
    """STH01 learn telegram: capability bits 4 (temp) and 5 (humidity)."""
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
    """Battery level 0 in flags byte -> weak."""
    payload = parse_sensor_payload(bytes([0x00, 0x40, 0x14, 0x0A, 0x46, 0x00, 0x00, 0x00]))
    assert isinstance(payload, SensorMeasurementPayload)
    assert payload.has_battery
    assert payload.battery_level == BatteryLevel.WEAK
    assert payload.battery_is_weak


def test_measurement_should_ignore_bit() -> None:
    """Spec Table 6 bit 1: host should ignore this data bit."""
    payload = parse_sensor_payload(bytes([0x00, 0x40, 0x16, 0x0A, 0x46, 0x00, 0x00, 0x00]))
    assert isinstance(payload, SensorMeasurementPayload)
    assert payload.should_ignore


def test_measurement_with_reference_value() -> None:
    """Bit 0 set: reference value present (same scale as primary)."""
    payload = parse_sensor_payload(bytes([0x00, 0x40, 0x15, 0x0A, 0x46, 0x09, 0xC4, 0x00]))
    assert isinstance(payload, SensorMeasurementPayload)
    assert payload.has_reference
    assert payload.reference_temperature_celsius == pytest.approx(25.0)


def test_legacy_rx21_temperature_and_humidity() -> None:
    """RX21 Table 6: wire type 4 = temp, 5 = humidity, raw / 10."""
    temp = parse_sensor_payload(
        bytes([0x00, 0x40, 0x10, 0x01, 0x07, 0x00, 0x00, 0x00]),
        payload_format=SensorPayloadFormat.LEGACY_RX21,
    )
    assert isinstance(temp, SensorMeasurementPayload)
    assert temp.wire_measurement_type == 4
    assert temp.measurement_type == MeasurementType.TEMPERATURE
    assert temp.temperature_celsius == pytest.approx(26.3)

    humidity = parse_sensor_payload(
        bytes([0x00, 0x40, 0x14, 0x02, 0x52, 0x00, 0x00, 0x00]),
        payload_format=SensorPayloadFormat.LEGACY_RX21,
    )
    assert isinstance(humidity, SensorMeasurementPayload)
    assert humidity.wire_measurement_type == 5
    assert humidity.measurement_type == MeasurementType.HUMIDITY
    assert humidity.humidity_percent == pytest.approx(59.4)
