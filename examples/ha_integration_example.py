#!/usr/bin/env python3
"""Example: Home Assistant Custom Component Integration Pattern.

This example demonstrates how to integrate the easywave_rx_module library
with Home Assistant using async patterns. It shows:

1. Async device creation and initialization
2. Safe error handling with timeouts
3. Periodic health checks with ping
4. Graceful disconnect and reconnection
5. Entity state management pattern

This is the recommended pattern for Home Assistant integration.
NOT a complete HA component, but shows the architectural pattern.

Home Assistant Requirements:
    - Python 3.11+
    - async/await throughout
    - No blocking calls in event loop
    - Proper error handling with timeouts
"""

import asyncio
import logging
from typing import Any

# Import the ASYNC API (Primary for HA)
from easywave_rx_module import AsyncDeviceFactory

_LOGGER = logging.getLogger(__name__)


class EasywaveCoordinator:
    """Coordinator for Home Assistant integration.

    This is a simplified version of how a HA integration would work:
    - Initialize device asynchronously
    - Periodic health checks
    - Safe error handling and reconnection
    - Integration with HA entity platform
    """

    def __init__(
        self,
        hass_name: str,  # Would be: hass.data["core"]["config_dir"]
        device_id: str,
        port: str,
        timeout: float = 5.0,
    ) -> None:
        """Initialize coordinator.

        Args:
            hass_name: Home Assistant instance name (for logging)
            device_id: Device type (e.g., "RX22", "RX11", "RX09")
            port: Serial port path
            timeout: Default timeout for operations
        """
        self.hass_name = hass_name
        self.device_id = device_id
        self.port = port
        self.timeout = timeout

        self._device = None
        self._available = False
        self._health_check_task = None

    async def async_setup(self) -> bool:
        """Set up coordinator asynchronously.

        Called during HA startup. Returns True if successful.

        Returns:
            True if device initialized successfully, False otherwise
        """
        try:
            _LOGGER.info(
                "Setting up EASYWAVE device: %s on port %s",
                self.device_id,
                self.port
            )

            # Create async device instance
            # ✅ This is NON-BLOCKING!
            self._device = await AsyncDeviceFactory.create(
                self.device_id,
                port=self.port,
                timeout=self.timeout
            )

            # Get device info
            info = await self._device.get_device_info()
            _LOGGER.debug("Device info: %s", info)

            # Verify device is accessible
            if not await self._device.ping_request(timeout=3.0):
                _LOGGER.error("Device not responding to ping")
                return False

            self._available = True

            # Start periodic health check
            self._health_check_task = asyncio.create_task(
                self._health_check_loop()
            )

            _LOGGER.info("EASYWAVE device setup complete")
            return True

        except Exception as e:
            _LOGGER.error("Failed to set up device: %s", e)
            self._available = False
            return False

    async def async_teardown(self) -> None:
        """Tear down coordinator (called on HA shutdown).

        Cancels health check and disconnects device.
        """
        # Cancel health check
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Disconnect device
        if self._device:
            try:
                await self._device.disconnect()
            except Exception as e:
                _LOGGER.warning("Error disconnecting device: %s", e)

        self._available = False

    async def _health_check_loop(self) -> None:
        """Periodic health check: ping device every 30 seconds."""
        while True:
            try:
                # Wait 30 seconds between checks (HA pattern)
                await asyncio.sleep(30.0)

                if not self._device:
                    continue

                # Ping device - ✅ non-blocking!
                success = await self._device.ping_request(timeout=3.0)

                if success and not self._available:
                    _LOGGER.info("Device recovered (was offline)")
                    self._available = True

                elif not success and self._available:
                    _LOGGER.warning("Device lost connection")
                    self._available = False

            except asyncio.CancelledError:
                _LOGGER.debug("Health check task cancelled")
                break
            except Exception as e:
                _LOGGER.error("Health check error: %s", e)

    async def async_send_command(
        self,
        gateway_id: int,
        button: int,
    ) -> bool:
        """Send command to device (example for entity controllers).

        This is how an entity would send a command through the coordinator.

        Args:
            gateway_id: Target gateway ID
            button: Button code (0-3 for RxModule, 'A'-'D' for RX09)

        Returns:
            True if successful, False on error
        """
        if not self._available or not self._device:
            _LOGGER.warning("Device not available for command")
            return False

        try:
            # For RxModule devices (RX11, RX22, etc.)
            if hasattr(self._device, "ew_send_cmd_request"):
                result, data = await self._device.ew_send_cmd_request(
                    gateway_id,
                    button
                )
                return result == 0  # Success if error code 0

            # For RX09 device
            elif hasattr(self._device, "send_telegramm"):
                result, response = await self._device.send_telegramm(
                    gateway_id,
                    str(button)
                )
                return result == 0

        except asyncio.TimeoutError:
            _LOGGER.error("Command timeout")
        except Exception as e:
            _LOGGER.error("Send command error: %s", e)

        return False

    @property
    def available(self) -> bool:
        """Whether device is currently available."""
        return self._available

    @property
    def device(self) -> Any:
        """Access to underlying device (for advanced use)."""
        return self._device


async def main_example():
    """Example: Set up coordinator and verify it works.

    This would be called from HA async_setup_platform in an integration.
    """
    # Setup coordinator (simulating HA initialization)
    coordinator = EasywaveCoordinator(
        hass_name="home-assistant",
        device_id="RX22",  # Or RX11, RX09, etc.
        port="/dev/ttyAMA0",  # Raspberry Pi serial port
        timeout=5.0
    )

    # Setup device
    if not await coordinator.async_setup():
        _LOGGER.error("Setup failed!")
        return

    # Simulate HA operations for 10 seconds
    try:
        # Get device info
        if coordinator.device:
            info = await coordinator.device.get_device_info()
            print(f"\n📱 Device Info: {info}")

            functions = await coordinator.device.get_available_functions()
            print(f"📋 Available Functions: {len(functions)}")

        # Simulate command sending
        print("\n🔄 Sending test commands...")
        success = await coordinator.async_send_command(
            gateway_id=123456,
            button=0
        )
        print(f"   Command result: {'✓ Success' if success else '✗ Failed'}")

        # Keep running for a bit to show health checks
        print("\n⏳ Coordinator running (health checks every 30s)")
        print("   Status:", "Available" if coordinator.available else "Offline")

        await asyncio.sleep(2.0)

        print("\n" + "="*60)
        print("✅ Coordinator example complete (teardown now)")

    finally:
        # Teardown (simulating HA shutdown)
        await coordinator.async_teardown()
        print("✓ Coordinator shut down cleanly\n")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("\n" + "="*60)
    print("🏠 Home Assistant Integration Pattern Example")
    print("="*60)

    # Run example (requires real device on port)
    # For testing, it will fail on device access, but shows the pattern
    try:
        asyncio.run(main_example())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        print("\n💡 This is expected if device is not connected.")
        print("   The example demonstrates the architectural pattern anyway.")
