"""Tests for transceiver capability profiles."""

from __future__ import annotations

import pytest

from easywave_home_control.gateway import (
    EntityKind,
    GatewayProtocol,
    TransceiverProfile,
    UnsupportedProtocolError,
    create_gateway,
    get_transceiver_profile,
    list_transceiver_ids,
    register_transceiver_profile,
)
from easywave_home_control.protocols.rx11_rx2x.protocol import DeviceType


def test_builtin_profiles_cover_rx_module_and_rx09() -> None:
    ids = list_transceiver_ids()
    assert "RX11" in ids
    assert "RX09" in ids
    assert "RX22" in ids


def test_rx11_entity_kinds() -> None:
    profile = get_transceiver_profile("RX11")
    kinds = profile.supported_entity_kinds()
    assert EntityKind.EASYWAVE_TRANSMITTER in kinds
    assert EntityKind.EASYWAVE_RECEIVER in kinds
    assert EntityKind.EASYWAVE_NEO_RECEIVER in kinds
    assert EntityKind.EASYWAVE_NEO_SENSOR in kinds
    assert EntityKind.SECWAVE_TRANSMITTER in kinds
    assert EntityKind.SECWAVE_RECEIVER in kinds


def test_rx11_supports_all_protocols_and_ewb_types() -> None:
    profile = get_transceiver_profile("RX11")
    assert profile.supports_protocol(GatewayProtocol.EW)
    assert profile.supports_protocol(GatewayProtocol.EWB)
    assert profile.supports_protocol(GatewayProtocol.SEC)
    assert profile.supports_ewb_device_type(DeviceType.EWB_DT_SWITCH)
    assert profile.supports_entity_kind(EntityKind.EASYWAVE_NEO_RECEIVER)
    assert profile.supports_entity_kind(EntityKind.SECWAVE_TRANSMITTER)
    assert profile.usb_discovery


def test_rx09_supports_easywave_transmitter_and_receiver_only() -> None:
    profile = get_transceiver_profile("RX09")
    kinds = profile.supported_entity_kinds()
    assert kinds == frozenset(
        {EntityKind.EASYWAVE_TRANSMITTER, EntityKind.EASYWAVE_RECEIVER}
    )
    assert profile.supports_entity_kind(EntityKind.EASYWAVE_RECEIVER)
    assert not profile.supports_entity_kind(EntityKind.EASYWAVE_NEO_SENSOR)


def test_register_successor_profile() -> None:
    successor = TransceiverProfile(
        id="RX11_TEST",
        family=get_transceiver_profile("RX11").family,
        protocols=frozenset({GatewayProtocol.EW, GatewayProtocol.EWB}),
        ewb_device_types=frozenset({DeviceType.EWB_DT_SWITCH}),
        usb_discovery=True,
        usb_ids=frozenset({(0x155A, 0x9999)}),
        display_name="RX11 Test Successor",
    )
    register_transceiver_profile(successor)
    loaded = get_transceiver_profile("RX11_TEST")
    kinds = loaded.supported_entity_kinds()
    assert EntityKind.SECWAVE_RECEIVER not in kinds
    assert EntityKind.EASYWAVE_RECEIVER in kinds
    assert loaded.supports_ewb_device_type(DeviceType.EWB_DT_SWITCH)
    assert not loaded.supports_ewb_device_type(DeviceType.EWB_DT_MOTOR)


def test_create_gateway_selects_rx09_class() -> None:
    gateway = create_gateway("RX09")
    assert gateway.transceiver_id == "RX09"
    assert gateway.profile.supports_protocol(GatewayProtocol.EW)


def test_rx09_ewb_facade_raises() -> None:
    gateway = create_gateway("RX09")
    with pytest.raises(UnsupportedProtocolError):
        gateway.ewb.join_device(b"\x00" * 16)
