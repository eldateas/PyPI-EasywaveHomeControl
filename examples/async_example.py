#!/usr/bin/env python3
"""Simple async example for Home Assistant integration.

This is the primary reference for using the library with Home Assistant.
Shows the clean async/await API with no blocking calls.
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from easywave_rx_module import AsyncDeviceFactory

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
_LOGGER = logging.getLogger(__name__)


async def main():
    """Demonstrate async device usage."""
    print("\n" + "=" * 70)
    print("🏠 ASYNC API - Home Assistant Compatible")
    print("=" * 70 + "\n")

    device = None
    try:
        # 1. Create and connect to device
        # Note: AsyncDeviceFactory.create() calls connect() internally!
        print("📱 Creating RX22 device (with auto-connect)...")
        device = await AsyncDeviceFactory.create(
            "RX22", port="/dev/ttyUSB0", timeout=5.0  # or "/dev/ttyAMA0" for Raspberry Pi
        )
        print("✓ Device created and connected\n")

        # 2. Get device info
        print("ℹ️  Device Information:")
        info = await device.get_device_info()
        for key, value in sorted(info.items()):
            print(f"   {key:20} {value}")

        # 3. Get available functions
        print("\n📋 Available Functions:")
        functions = await device.get_available_functions()
        for i, func_name in enumerate(list(functions.keys())[:5], 1):
            print(f"   {i}. {func_name}")
        print(f"   ... and {len(functions) - 5} more")

        # 4. Test device connectivity
        print("\n🔍 Device Status:")
        connected = await device.ping_request(timeout=3.0)
        print(f"   Connected: {'✓ Yes' if connected else '✗ No'}")

        # 5. Query hardware version
        if connected:
            error, version = await device.query_hw_version()
            print(f"   Hardware: {version if error == 0 else 'N/A'}")

            error, version = await device.query_fw_version()
            print(f"   Firmware: {version if error == 0 else 'N/A'}")

        print("\n" + "=" * 70)
        print("✅ Async API Example Complete")
        print("=" * 70 + "\n")

    except Exception as e:
        _LOGGER.error("Error: %s", e)
        print(f"\n⚠️  Error: {e}")
        print("(This is expected if device is not connected)")

    finally:
        if device:
            print("🔌 Disconnecting...")
            # IMPORTANT: Always disconnect when done!
            await device.disconnect()
            print("✓ Disconnected\n")


if __name__ == "__main__":
    asyncio.run(main())
