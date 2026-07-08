"""Factory for transceiver gateways."""

from __future__ import annotations

from dataclasses import replace

from .base import BaseTransceiverGateway, GatewayCallbacks
from .capabilities import TransceiverFamily
from .config import GatewayConfig
from .gateway import RxModuleGateway
from .profiles import get_transceiver_profile
from .rx09_gateway import Rx09Gateway


def create_gateway(
    transceiver_id: str | None = None,
    config: GatewayConfig | None = None,
    *,
    callbacks: GatewayCallbacks | None = None,
) -> BaseTransceiverGateway:
    """Create the appropriate gateway for a transceiver profile."""
    if config is None:
        if transceiver_id is None:
            raise ValueError("transceiver_id or config is required")
        config = GatewayConfig(transceiver_id=transceiver_id)
    elif transceiver_id is not None:
        config = replace(config, transceiver_id=transceiver_id)

    profile = get_transceiver_profile(config.transceiver_id)
    if profile.family == TransceiverFamily.RX09:
        return Rx09Gateway(config, callbacks=callbacks)
    return RxModuleGateway(config, callbacks=callbacks)
