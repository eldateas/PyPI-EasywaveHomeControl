#!/usr/bin/env python3
"""Example: Home Assistant Integration with RX11 and RX09.

Demonstrates how to integrate the Easywave RX11/RX09 receivers into
Home Assistant as a long-running service.

Features:
- Automatic device discovery on startup
- Continuous background listening for button presses
- Event integration with Home Assistant event bus
- Graceful shutdown handling
- Error recovery and reconnection

This example shows the pattern for creating a Home Assistant
custom component using the easywave-rx-module library.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

from easywave_rx_module import RX09Device, RX11Device

_LOGGER = logging.getLogger(__name__)


@dataclass
class ButtonEvent:
    """Represents a button press event."""

    transmitter: bytes
    button: int
    info_type: int
    info_data: bytes
    timestamp: float


class RxModuleHA:
    """Home Assistant integration for Easywave RX modules.
    
    Handles:
    - Device lifecycle (connect/disconnect)
    - Background listening for button presses
    - Event callbacks to Home Assistant
    - Error handling and recovery
    """

    def __init__(
        self,
        device_class: Union[type[RX11Device], type[RX09Device]],
        port: str,
        event_callback: Optional[Callable[[ButtonEvent], None]] = None,
    ):
        """Initialize RX module HA integration.
        
        Args:
            device_class: Device class to use (RX11Device, RX09Device, etc.)
            port: Serial port (e.g., "/dev/ttyUSB0" or "COM3")
            event_callback: Optional callback for button events
        """
        self.device_class = device_class
        self.port = port
        self.event_callback = event_callback
        self.device: Optional[Union[RX11Device, RX09Device]] = None
        self._listening = False
        self._listen_task: Optional[asyncio.Task[None]] = None

    async def connect(self) -> bool:
        """Connect to RX module.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            _LOGGER.info(
                "Connecting to %s on port %s...", self.device_class.__name__, self.port
            )
            self.device = await self.device_class.create(
                port=self.port, timeout=10.0
            )
            _LOGGER.info("Successfully connected to %s", self.device_class.__name__)
            return True
        except Exception as e:
            _LOGGER.error("Failed to connect to %s: %s", self.device_class.__name__, e)
            self.device = None
            return False

    async def disconnect(self) -> None:
        """Disconnect from RX module."""
        # Stop listening first
        await self.stop_listening()

        # Then disconnect device
        if self.device:
            try:
                await self.device.disconnect()
                _LOGGER.info("Disconnected from %s", self.device_class.__name__)
            except Exception as e:
                _LOGGER.error("Error disconnecting: %s", e)
            finally:
                self.device = None

    async def start_listening(self) -> None:
        """Start background listening for button presses.
        
        The listening task will:
        - Listen indefinitely for button presses
        - Call event_callback for each press
        - Handle disconnections and reconnect
        - Continue until stop_listening() is called
        """
        if self._listening:
            _LOGGER.warning("Already listening")
            return

        if not self.device:
            _LOGGER.error("Not connected")
            return

        _LOGGER.info("Starting button listener for %s", self.device_class.__name__)
        self._listening = True
        self._listen_task = asyncio.create_task(self._listen_loop())

    async def stop_listening(self) -> None:
        """Stop background listening."""
        if not self._listening:
            return

        _LOGGER.info("Stopping listener")
        self._listening = False

        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            finally:
                self._listen_task = None

    async def _listen_loop(self) -> None:
        """Internal listening loop (runs in background)."""
        if not self.device or not self._listening:
            return

        while self._listening and self.device:
            try:
                # Listen for button presses with no timeout
                result, info_type, transmitter, info_data = (  # type: ignore[misc]
                    await self.device.ew_rcv_button_request(timeout=None)  # type: ignore[attr-defined]
                )

                if result == self.device.ErrorCode.SUCCESS and self._listening:  # type: ignore[attr-defined]
                    # Fire event callback
                    event = ButtonEvent(
                        transmitter=transmitter,  # type: ignore[arg-type]
                        button=info_type,  # type: ignore[arg-type]
                        info_type=info_type,  # type: ignore[arg-type]
                        info_data=info_data,  # type: ignore[arg-type]
                        timestamp=asyncio.get_event_loop().time(),
                    )
                    if self.event_callback:
                        self.event_callback(event)

            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.error("Error in listen loop: %s", e)
                if self._listening:
                    # Wait before retry
                    await asyncio.sleep(5)


class HasButtonEntity:
    """Simplified Home Assistant button entity.
    
    A real implementation would extend hass.helpers.entity.Entity
    """

    def __init__(self, unique_id: str, name: str):
        """Initialize button entity."""
        self.unique_id = unique_id
        self.name = name
        self.last_updated: Optional[float] = None

    async def async_handle_event(self, event: ButtonEvent) -> None:
        """Handle button event from RX module."""
        self.last_updated = event.timestamp
        _LOGGER.info(
            "Button event on %s: transmitter=%s, data=%s",
            self.name,
            event.transmitter.hex(),
            event.info_data.hex(),
        )


# Example Home Assistant setup functions


async def setup_rx11_integration(hass_config: dict[str, Any]) -> Optional[RxModuleHA]:
    """Set up RX11 integration.
    
    Args:
        hass_config: Home Assistant configuration dict with:
            - "port": Serial port for RX11
    
    Returns:
        RxModuleHA instance if successful, None otherwise
    """
    _LOGGER.info("Setting up RX11 Easywave integration")

    port = hass_config.get("port", "/dev/ttyUSB0")

    # Create integration
    rx11_integration = RxModuleHA(
        device_class=RX11Device,
        port=port,
        event_callback=_on_button_event,
    )

    # Connect
    if not await rx11_integration.connect():
        return None

    # Start listening
    await rx11_integration.start_listening()

    _LOGGER.info("RX11 integration setup complete")
    return rx11_integration


async def setup_rx09_integration(hass_config: dict[str, Any]) -> Optional[RxModuleHA]:
    """Set up RX09 integration.
    
    Args:
        hass_config: Home Assistant configuration dict with:
            - "port": Serial port for RX09
    
    Returns:
        RxModuleHA instance if successful, None otherwise
    """
    _LOGGER.info("Setting up RX09 Easywave integration")

    port = hass_config.get("port", "/dev/ttyUSB1")

    # Create integration
    rx09_integration = RxModuleHA(
        device_class=RX09Device,
        port=port,
        event_callback=_on_button_event,
    )

    # Connect
    if not await rx09_integration.connect():
        return None

    # Start listening (RX09 has limited button detection)
    await rx09_integration.start_listening()

    _LOGGER.info("RX09 integration setup complete")
    return rx09_integration


def _on_button_event(event: ButtonEvent) -> None:
    """Callback for button events.
    
    In real HA integration, this would:
    - Fire hass.bus.async_fire("easywave.button_pressed", {...})
    - Update entity state
    - Trigger automations
    """
    _LOGGER.info(
        "Button pressed: %s (data: %s)",
        event.transmitter.hex(),
        event.info_data.hex(),
    )


async def example_single_device():
    """Example: Single RX11 device with event handler."""
    print("\n" + "=" * 80)
    print("Home Assistant Example: Single RX11 Device")
    print("=" * 80 + "\n")

    config = {"port": "/dev/ttyUSB0"}
    rx11: Optional[RxModuleHA] = await setup_rx11_integration(config)

    if rx11:
        try:
            print("✓ RX11 listening for button presses (30 seconds)...\n")
            await asyncio.sleep(30)
        except KeyboardInterrupt:
            print("\n\nInterrupted")
        finally:
            await rx11.disconnect()


async def example_multiple_devices():
    """Example: Multiple RX modules (RX11 + RX09)."""
    print("\n" + "=" * 80)
    print("Home Assistant Example: Multiple RX Modules")
    print("=" * 80 + "\n")

    rx11_config = {"port": "/dev/ttyUSB0"}
    rx09_config = {"port": "/dev/ttyUSB1"}

    rx11: Optional[RxModuleHA] = await setup_rx11_integration(rx11_config)
    rx09: Optional[RxModuleHA] = await setup_rx09_integration(rx09_config)

    if rx11 or rx09:
        try:
            print("✓ Listeners active for both devices (30 seconds)...\n")
            await asyncio.sleep(30)
        except KeyboardInterrupt:
            print("\n\nInterrupted")
        finally:
            if rx11:
                await rx11.disconnect()
            if rx09:
                await rx09.disconnect()


async def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║      HOME ASSISTANT INTEGRATION EXAMPLES (RX11 & RX09)                    ║
║                                                                            ║
║ Demonstrates how to integrate Easywave receivers as services:             ║
║ - Single device integration                                                ║
║ - Multiple device setup                                                    ║
║ - Background listening with callbacks                                      ║
║ - Graceful shutdown                                                        ║
║ - Error handling and recovery                                              ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

    # Run single device example
    await example_single_device()

    # Uncomment to run multiple devices example
    # await example_multiple_devices()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nProgram interrupted.\n")
