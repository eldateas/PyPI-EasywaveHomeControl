"""Transceiver capability model for gateway integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class GatewayProtocol(str, Enum):
    """Radio / codec protocol stacks exposed by a transceiver profile."""

    EW = "ew"
    """Easywave Basic (classic button telegrams and receiver commands)."""

    EWB = "ewb"
    """Easywave Bidi neo (bidirectional receivers, sensors, state control)."""

    SEC = "sec"
    """Secwave security telegrams."""


class TransceiverFamily(str, Enum):
    """Hardware protocol family."""

    RX_MODULE = "rx_module"
    """Binary IRP/ICP (RX11, RX21, RX22, RX25, and future successors)."""

    RX09 = "rx09"
    """ASCII text protocol (RX09 / RTR09)."""


class EntityKind(str, Enum):
    """Integration device categories exposed per transceiver profile.

    Easywave Basic and Secwave split into transmitter vs. receiver roles.
    EWneo (EWB) stays bidirectional — neo receivers are controlled and emit
    state/events on the same protocol path.
    """

    EASYWAVE_TRANSMITTER = "easywave_transmitter"
    """Classic Easywave button transmitters (received via EW_RCV_EX)."""

    EASYWAVE_RECEIVER = "easywave_receiver"
    """Classic Easywave receivers (controlled via EW_SEND_CMD)."""

    EASYWAVE_NEO_RECEIVER = "easywave_neo_receiver"
    """EWneo bidirectional receivers (EWB join, change/query state, EWB_RCV)."""

    EASYWAVE_NEO_SENSOR = "easywave_neo_sensor"
    """EWneo DATA sensors (e.g. STH01 via EW_RCV_EX)."""

    SECWAVE_TRANSMITTER = "secwave_transmitter"
    """Secwave transmitters (received via SEC_RCV / SEC_LEARN)."""

    SECWAVE_RECEIVER = "secwave_receiver"
    """Secwave receivers (controlled via SEC_SEND_* / SEC_REPLY_QUERY)."""


_ENTITY_KIND_PROTOCOL: dict[EntityKind, GatewayProtocol] = {
    EntityKind.EASYWAVE_TRANSMITTER: GatewayProtocol.EW,
    EntityKind.EASYWAVE_RECEIVER: GatewayProtocol.EW,
    EntityKind.EASYWAVE_NEO_RECEIVER: GatewayProtocol.EWB,
    EntityKind.EASYWAVE_NEO_SENSOR: GatewayProtocol.EWB,
    EntityKind.SECWAVE_TRANSMITTER: GatewayProtocol.SEC,
    EntityKind.SECWAVE_RECEIVER: GatewayProtocol.SEC,
}


@dataclass(frozen=True, slots=True)
class TransceiverProfile:
    """Capabilities of a transceiver model for integration UIs and validation.

    Home Assistant (or other integrations) should use this to decide which
    device types, config flows, and codec paths to expose for a given stick.
    Future successors (e.g. a new RX11 USB generation) register as additional
    profiles with their own ``id``, ``usb_ids``, and capability sets.
    """

    id: str
    family: TransceiverFamily
    protocols: frozenset[GatewayProtocol]
    ewb_device_types: frozenset[int] = field(default_factory=frozenset)
    """Supported EWB neo receiver ``DeviceType`` values (empty when no EWB)."""

    default_baudrate: int = 115200
    usb_discovery: bool = False
    usb_ids: frozenset[tuple[int, int]] = field(default_factory=frozenset)
    display_name: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        if not self.display_name:
            object.__setattr__(self, "display_name", self.id)

    def supports_protocol(self, protocol: GatewayProtocol) -> bool:
        return protocol in self.protocols

    def supports_ewb_device_type(self, device_type: int) -> bool:
        return device_type in self.ewb_device_types

    def supported_entity_kinds(self) -> frozenset[EntityKind]:
        """Return all entity kinds this transceiver can host."""
        return frozenset(
            kind
            for kind, protocol in _ENTITY_KIND_PROTOCOL.items()
            if protocol in self.protocols
        )

    def supports_entity_kind(self, kind: EntityKind) -> bool:
        """Return whether an integration entity kind is valid for this profile."""
        protocol = _ENTITY_KIND_PROTOCOL.get(kind)
        return protocol in self.protocols if protocol is not None else False


class UnsupportedProtocolError(RuntimeError):
    """Raised when a facade method is used on an unsupported transceiver profile."""

    def __init__(self, transceiver_id: str, protocol: GatewayProtocol) -> None:
        super().__init__(
            f"Transceiver {transceiver_id!r} does not support protocol {protocol.value!r}"
        )
        self.transceiver_id = transceiver_id
        self.protocol = protocol
