"""Gateway layer — connection lifecycle and protocol facades for transceivers."""

from .base import (
    BaseTransceiverGateway,
    GatewayCallbacks,
    GatewayConnectionState,
    GatewayInfo,
)
from .capabilities import (
    EntityKind,
    GatewayProtocol,
    TransceiverFamily,
    TransceiverProfile,
    UnsupportedProtocolError,
)
from .config import DEFAULT_RX11_USB_IDS, GatewayConfig
from .device_registry import RX_MODULE_DEVICE_TYPES, RxModuleDeviceType, create_rx_device
from .facades import EasywaveBasicFacade, EwbNeoFacade, SecwaveFacade
from .factory import create_gateway
from .gateway import EasywaveGateway, RxModuleGateway
from .profiles import (
    get_transceiver_profile,
    list_transceiver_ids,
    list_transceiver_profiles,
    profiles_for_protocol,
    register_transceiver_profile,
)
from .rx09_gateway import Rx09Gateway

__all__ = [
    "DEFAULT_RX11_USB_IDS",
    "EntityKind",
    "RX_MODULE_DEVICE_TYPES",
    "BaseTransceiverGateway",
    "EasywaveBasicFacade",
    "EasywaveGateway",
    "EwbNeoFacade",
    "GatewayCallbacks",
    "GatewayConfig",
    "GatewayConnectionState",
    "GatewayInfo",
    "GatewayProtocol",
    "Rx09Gateway",
    "RxModuleDeviceType",
    "RxModuleGateway",
    "SecwaveFacade",
    "TransceiverFamily",
    "TransceiverProfile",
    "UnsupportedProtocolError",
    "create_gateway",
    "create_rx_device",
    "get_transceiver_profile",
    "list_transceiver_ids",
    "list_transceiver_profiles",
    "profiles_for_protocol",
    "register_transceiver_profile",
]
