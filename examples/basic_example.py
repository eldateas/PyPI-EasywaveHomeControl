#!/usr/bin/env python3
"""Simple async example of using the easywave-rx-module library.

This example demonstrates the basic async API:
- Creating a device with AsyncDeviceFactory
- Querying device information
- Testing device connectivity
- Proper cleanup with disconnect()
"""

import asyncio

from easywave_rx_module import AsyncDeviceFactory, ErrorCode


async def main():
    """Main async example."""
    device = None
    try:
        # Create module instance - connects automatically!
        print("🔌 Connecting to RX22 device...")
        device = await AsyncDeviceFactory.create(
            "RX22", port="/dev/ttyUSB0", timeout=5.0  # or /dev/ttyAMA0 for Raspberry Pi
        )
        print("✓ Connected\n")

        # Get device info
        print("📋 Device Status:")
        print(f"  Connected: {device.is_connected}")
        print(f"  Status: {device.connection_status}\n")

        # Query hardware version
        print("🔍 Hardware Information:")
        result, hw_ver = await device.query_hw_version(timeout=5.0)
        if result == ErrorCode.SUCCESS:
            print(f"  Hardware: {hw_ver.hex()}")
        else:
            print(f"  Hardware query failed: {result}")

        # Query firmware version
        result, major, minor, incomplete = await device.query_fw_version(timeout=5.0)
        if result == ErrorCode.SUCCESS:
            incomplete_str = " (incomplete)" if incomplete else ""
            print(f"  Firmware: {major}.{minor}{incomplete_str}")
        else:
            print(f"  Firmware query failed: {result}")

        # Get device info (status, etc.)
        info = await device.get_device_info()
        print("\n📊 Device Info:")
        for key, value in info.items():
            print(f"  {key}: {value}")

        # Get available functions
        functions = await device.get_available_functions()
        print(f"\n📡 Available Functions ({len(functions)}):")
        for i, name in enumerate(list(functions.keys())[:5], 1):
            print(f"  {i}. {name}")
        if len(functions) > 5:
            print(f"  ... and {len(functions) - 5} more")

        # Test connectivity
        print("\n🔗 Device Connectivity:")
        connected = await device.ping_request(timeout=3.0)
        print(f"  Ping response: {'✓ OK' if connected else '✗ Timeout'}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Always disconnect!
        if device:
            print("\n🔌 Disconnecting...")
            await device.disconnect()
            print("✓ Disconnected")


if __name__ == "__main__":
    asyncio.run(main())
