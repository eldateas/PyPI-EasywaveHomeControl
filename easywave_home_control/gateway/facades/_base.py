"""Base class for gateway protocol facades."""

from __future__ import annotations

from ..capabilities import GatewayProtocol, TransceiverProfile, UnsupportedProtocolError
from ..io import GatewayIO, GatewayIOHost


class FacadeBase:
    """Protocol facade bound to a gateway host and transceiver profile."""

    def __init__(
        self,
        host: GatewayIOHost,
        protocol: GatewayProtocol,
        profile: TransceiverProfile,
    ) -> None:
        self._host = host
        self._protocol = protocol
        self._profile = profile
        self._io = GatewayIO(host)

    def _ensure_supported(self) -> None:
        if not self._profile.supports_protocol(self._protocol):
            raise UnsupportedProtocolError(self._profile.id, self._protocol)
