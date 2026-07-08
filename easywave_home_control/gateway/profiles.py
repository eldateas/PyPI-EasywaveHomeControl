"""Built-in transceiver profiles and registration for extensions."""

from __future__ import annotations

from ..protocols.rx11_rx2x.protocol import DeviceType
from .capabilities import (
    GatewayProtocol,
    TransceiverFamily,
    TransceiverProfile,
)
from .config import DEFAULT_RX11_USB_IDS

_RX_MODULE_PROTOCOLS: frozenset[GatewayProtocol] = frozenset(
    {GatewayProtocol.EW, GatewayProtocol.EWB, GatewayProtocol.SEC}
)

_RX_MODULE_EWB_DEVICE_TYPES: frozenset[int] = frozenset(
    {
        DeviceType.EWB_DT_BIDI_TR,
        DeviceType.EWB_DT_SWITCH,
        DeviceType.EWB_DT_DIMMER,
        DeviceType.EWB_DT_MOTOR,
        DeviceType.EWB_DT_DUAL_SWITCH,
        DeviceType.EWB_DT_QUAD_SWITCH,
        DeviceType.EWB_DT_DUAL_MOTOR,
        DeviceType.EWB_DT_QUAD_MOTOR,
    }
)

# Example placeholder for a future RX11 successor with a subset of capabilities.
# Integrations register real profiles when hardware ships:
#
# register_transceiver_profile(TransceiverProfile(
#     id="RX11_PRO",
#     family=TransceiverFamily.RX_MODULE,
#     protocols=frozenset({GatewayProtocol.EW, GatewayProtocol.EWB}),
#     ewb_device_types=frozenset({DeviceType.EWB_DT_SWITCH, DeviceType.EWB_DT_DIMMER}),
#     usb_discovery=True,
#     usb_ids=frozenset({(0x155A, 0x1015)}),
#     display_name="RX11 Pro USB Transceiver",
# ))


def _rx_module_profile(
    transceiver_id: str,
    *,
    usb_discovery: bool,
    usb_ids: frozenset[tuple[int, int]],
    display_name: str,
) -> TransceiverProfile:
    return TransceiverProfile(
        id=transceiver_id,
        family=TransceiverFamily.RX_MODULE,
        protocols=_RX_MODULE_PROTOCOLS,
        ewb_device_types=_RX_MODULE_EWB_DEVICE_TYPES,
        default_baudrate=115200,
        usb_discovery=usb_discovery,
        usb_ids=usb_ids,
        display_name=display_name,
        description="Binary RxModule transceiver (EW, EWneo, Secwave).",
    )


_BUILTIN_PROFILES: dict[str, TransceiverProfile] = {
    "RX11": _rx_module_profile(
        "RX11",
        usb_discovery=True,
        usb_ids=DEFAULT_RX11_USB_IDS,
        display_name="RX11 USB Transceiver",
    ),
    "RX21": _rx_module_profile(
        "RX21",
        usb_discovery=False,
        usb_ids=frozenset(),
        display_name="RX21 Serial Module",
    ),
    "RX22": _rx_module_profile(
        "RX22",
        usb_discovery=False,
        usb_ids=frozenset(),
        display_name="RX22 Serial Module",
    ),
    "RX25": _rx_module_profile(
        "RX25",
        usb_discovery=False,
        usb_ids=frozenset(),
        display_name="RX25 Serial Module",
    ),
    "RX09": TransceiverProfile(
        id="RX09",
        family=TransceiverFamily.RX09,
        protocols=frozenset({GatewayProtocol.EW}),
        ewb_device_types=frozenset(),
        default_baudrate=57600,
        usb_discovery=False,
        usb_ids=frozenset(),
        display_name="RX09 USB Receiver",
        description="ASCII Easywave Basic only (no EWneo, no Secwave).",
    ),
}

_PROFILES: dict[str, TransceiverProfile] = dict(_BUILTIN_PROFILES)


def register_transceiver_profile(
    profile: TransceiverProfile,
    *,
    replace: bool = False,
) -> None:
    """Register or override a transceiver profile (e.g. future RX11 successor)."""
    key = profile.id.upper()
    if not replace and key in _PROFILES and key in _BUILTIN_PROFILES:
        raise ValueError(
            f"Built-in profile {key!r} cannot be replaced without replace=True"
        )
    _PROFILES[key] = profile


def get_transceiver_profile(transceiver_id: str) -> TransceiverProfile:
    """Return the capability profile for ``transceiver_id`` (case-insensitive)."""
    key = transceiver_id.upper()
    profile = _PROFILES.get(key)
    if profile is None:
        known = ", ".join(sorted(_PROFILES))
        raise ValueError(f"Unknown transceiver {transceiver_id!r}. Known: {known}")
    return profile


def list_transceiver_profiles() -> tuple[TransceiverProfile, ...]:
    """Return all registered transceiver profiles."""
    return tuple(_PROFILES[k] for k in sorted(_PROFILES))


def list_transceiver_ids() -> tuple[str, ...]:
    return tuple(sorted(_PROFILES))


def profiles_for_protocol(protocol: GatewayProtocol) -> tuple[TransceiverProfile, ...]:
    return tuple(p for p in list_transceiver_profiles() if p.supports_protocol(protocol))
