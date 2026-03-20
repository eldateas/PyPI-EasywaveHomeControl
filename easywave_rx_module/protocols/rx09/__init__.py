"""RX09 Protocol Family (ASCII Text-based Easywave Basic).

RX09 is a simplified Easywave receiver with a completely different protocol:
- ASCII text-based (not binary)
- Comma-separated commands
- CR (0x0D) line terminator
- 57600 baud (not 38400)
- Only basic Easywave functions (no Bidi, no Secwave)

This module exports both sync (legacy) and async (primary for HA) implementations.
"""

# Sync devices (legacy, will be removed)
from .devices import RX09Device
from .protocol import RX09Protocol

# Async devices (primary API for Home Assistant)
from .async_devices import AsyncRX09Device
from .async_protocol import AsyncRX09Protocol

__all__ = [
    "RX09Protocol",
    "RX09Device",
    "AsyncRX09Protocol",
    "AsyncRX09Device",
]
