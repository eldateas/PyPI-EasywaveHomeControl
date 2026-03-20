#!/usr/bin/env python3
"""Example: RxModule button receive with async API.

This example shows how to use the RxModule protocol to receive button
presses asynchronously using the async/await API.

Devices Supported:
- RX11: USB transceiver
- RX21: Serial module
- RX22: Serial module
- RX25: Serial module

Features:
- Create RxModule device asynchronously
- Listen for button press telegrams
- Handle errors with timeouts
- Proper async cleanup
"""

import asyncio
import logging

from easywave_rx_module import AsyncDeviceFactory, ErrorCode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
_LOGGER = logging.getLogger(__name__)


async def receive_button_presses():
    """Listen for RxModule button presses asynchronously."""
    print("\n" + "=" * 70)
    print("RxModule Button Receive Example (Async)")
    print("=" * 70 + "\n")

    device = None
    try:
        # Create RxModule device (e.g., RX22)
        print("📱 Creating RxModule device...")
        device = await AsyncDeviceFactory.create(
            "RX22", port="/dev/ttyUSB0", timeout=5.0
        )
        print("✓ Device created and connected\n")

        # Get device info
        info = await device.get_device_info()
        print("ℹ️  Device Information:")
        for key, value in sorted(info.items()):
            print(f"   {key:20} {value}")
        print()

        # Listen for button presses
        print("📡 Listening for RxModule button presses...")
        print("   (Send a button press from a transmitter)\n")

        # Try to receive a button press
        try:
            # This will wait up to 30 seconds for a button press
            # To cancel, press Ctrl+C
            result, info_type, transmitter, data = await device.ew_rcv_button_request(  # type: ignore[attr-defined]
                timeout=30.0
            )

            if result == ErrorCode.SUCCESS:
                print("✓ Button received!")
                print(f"  Info Type: {info_type:02X}")
                print(f"  Transmitter: {transmitter.hex()}")
                print(f"  Data: {data.hex()}")
            else:
                print(f"⚠️  Receive failed: error {result}")

        except asyncio.TimeoutError:
            print("⏱️  Timeout waiting for button press")

    except Exception as e:
        _LOGGER.error("Error: %s", e)
        print(f"❌ Error: {e}")

    finally:
        if device:
            print("🔌 Disconnecting...")
            await device.disconnect()
            print("✓ Disconnected\n")


async def receive_multiple_presses():
    """Listen for multiple button presses in sequence."""
    print("\n" + "=" * 70)
    print("RxModule Multiple Button Presses Example")
    print("=" * 70 + "\n")

    device = None
    try:
        # Create device
        device = await AsyncDeviceFactory.create("RX22", port="/dev/ttyUSB0", timeout=5.0)
        print("✓ Device created\n")
        print("📡 Waiting for button presses (5 total)...")
        print("   Press Ctrl+C to stop\n")

        press_count = 0
        while press_count < 5:
            try:
                result, info_type, transmitter, data = await device.ew_rcv_button_request(  # type: ignore[attr-defined]
                    timeout=10.0
                )

                if result == ErrorCode.SUCCESS:
                    press_count += 1
                    print(f"{press_count}. Transmitter: {transmitter.hex()}, Type: {info_type:02X}")
                else:
                    print(f"Error: {result}")

            except asyncio.TimeoutError:
                print("⏱️  Timeout - no button press received")
                break

        print(f"\n✓ Received {press_count} button press(es)")

    except Exception as e:
        _LOGGER.error("Error: %s", e)
        print(f"❌ Error: {e}")

    finally:
        if device:
            await device.disconnect()
            print("✓ Disconnected")


async def main():
    """Main entry point."""
    try:
        # Run the simple example
        await receive_button_presses()

        # Uncomment to run the multiple presses example
        # await receive_multiple_presses()

    except KeyboardInterrupt:
        print("\n\n⏸️  Interrupted by user")


if __name__ == "__main__":
    asyncio.run(main())
