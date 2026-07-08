"""RxModule device type registry for the gateway layer."""

from __future__ import annotations

from typing import Literal

from ..protocols.rx11_rx2x.devices import (
    RX11Device,
    RX21Device,
    RX22Device,
    RX25Device,
    RxModuleDevice,
)

RxModuleDeviceType = Literal["RX11", "RX21", "RX22", "RX25"]

RX_MODULE_DEVICE_TYPES: tuple[RxModuleDeviceType, ...] = (
    "RX11",
    "RX21",
    "RX22",
    "RX25",
)

_DEVICE_REGISTRY: dict[RxModuleDeviceType, type[RxModuleDevice]] = {
    "RX11": RX11Device,
    "RX21": RX21Device,
    "RX22": RX22Device,
    "RX25": RX25Device,
}


def create_rx_device(transceiver_id: str, port: str) -> RxModuleDevice:
    """Instantiate an unconnected RxModule device."""
    device_class = _DEVICE_REGISTRY.get(transceiver_id.upper())  # type: ignore[arg-type]
    if device_class is None:
        supported = ", ".join(RX_MODULE_DEVICE_TYPES)
        raise ValueError(f"Unknown RxModule transceiver {transceiver_id!r}. Supported: {supported}")
    return device_class(port=port)
