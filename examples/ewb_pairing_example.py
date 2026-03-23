#!/usr/bin/env python3
"""Example: Easywave Bidi Device Pairing and Learning (RX11 only).

Demonstrates the Easywave Bidi (EWB) device learning workflow:
1. Get gateway serial number (EWB_GET_FD_SERIAL)
2. Add filter with gateway serial number (EWB_ADD_NFILTER)
3. Join new device to gateway (EWB_JOIN_DEVICE)
4. Receive device type and receiver serial number on success

This is RX11 only - RX09 does not support Bidi protocol.

Important: Before learning a new device, ensure the device is in learning mode
(usually by pressing a specific button combination on the device).
"""

import asyncio
import logging
from typing import Optional

from easywave_home_control import RX11Device

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
_LOGGER = logging.getLogger(__name__)


async def ewb_pair_and_learn_device() -> None:
    """Learn new Easywave Bidi device with gateway serial number.
    
    Prerequisites:
    - RX11 connected and working
    - Device to be learned must be in learning mode
    
    Workflow:
    1. Load gateway serial number from RX11
    2. Add filter with gateway serial number
    3. Join (learn) new device with gateway
    4. Receive device type and serial number on success
    """
    print("\n" + "=" * 80)
    print("RX11: Easywave Bidi Device Learning with Gateway Serial")
    print("=" * 80 + "\n")

    device: Optional[RX11Device] = None
    try:
        # Create RX11 device
        print("📱 Creating RX11 USB Transceiver...")
        device = await RX11Device.create(
            port="/dev/ttyUSB0", timeout=5.0
        )
        print("✓ Device created and connected\n")

        # Step 1: Get gateway serial number
        print("📡 Step 1: Loading gateway serial number...")
        result, gateway_serial = await device.ewb_get_fd_serial_request(  # type: ignore[attr-defined]
            index=0, timeout=2.0
        )

        if result != RX11Device.ErrorCode.SUCCESS or gateway_serial == b"\x00" * 16:
            print("⚠️  No gateway found or error loading serial")
            return

        print(f"✓ Gateway serial: {gateway_serial.hex()}\n")

        # Step 2: Add filter with gateway serial number
        print("🔧 Step 2: Setting up filter with gateway serial...")
        result = await device.ewb_add_nfilter_request(  # type: ignore[attr-defined]
            gateway=gateway_serial, timeout=5.0
        )

        if result == RX11Device.ErrorCode.SUCCESS:
            print("✓ Filter configured with gateway serial\n")
        else:
            print(f"⚠️  Filter setup failed: error {result}\n")
            return

        # Step 3: Join (learn) new device
        print("📚 Step 3: Learning new device (30 seconds)...")
        print("   >> Put device in learning mode NOW <<\n")

        result, device_type, receiver_serial = await device.ewb_join_device_request(  # type: ignore[attr-defined]
            gateway=gateway_serial, timeout=30.0
        )

        if result == RX11Device.ErrorCode.SUCCESS:
            print("✓ Device learned successfully!\n")
            print(f"  Device Type:       0x{device_type:02X}")
            print(f"  Receiver Serial:   {receiver_serial.hex()}\n")
        else:
            print(f"⚠️  Device learning failed: error {result}\n")
            print("   Make sure device is in learning mode\n")

    except Exception as e:
        _LOGGER.error("Error: %s", e)
        print(f"❌ Error: {e}\n")

    finally:
        if device:
            print("🔌 Disconnecting...")
            await device.disconnect()
            print("✓ Disconnected\n")


async def ewb_listen_state_changes() -> None:
    """Simple listener for EWB state changes.
    
    Use this to continuously monitor state changes from already-learned devices.
    """
    print("\n" + "=" * 80)
    print("RX11: Easywave Bidi State Change Listener")
    print("=" * 80 + "\n")

    device: Optional[RX11Device] = None
    try:
        print("📱 Creating RX11 USB Transceiver...")
        device = await RX11Device.create(
            port="/dev/ttyUSB0", timeout=5.0
        )
        print("✓ Device created and connected\n")

        print("📡 Listening for EWB state changes (No timeout)...")
        print("   (Toggle your learned Easywave Bidi devices)\n")

        # Listen indefinitely for state changes
        while True:
            try:
                result, info_type, transmitter, info_data = await device.ewb_rcv_request(  # type: ignore[attr-defined]
                    timeout=None  # No timeout - listen indefinitely
                )

                if result == RX11Device.ErrorCode.SUCCESS:
                    print(f"✓ State change from {transmitter.hex()}")
                    print(f"  Info Type: 0x{info_type:02X}, Data: {info_data.hex()}")
                else:
                    print(f"⚠️  Error: {result}")

            except KeyboardInterrupt:
                print("\n📡 Listener stopped")
                break

    except Exception as e:
        _LOGGER.error("Error: %s", e)
        print(f"❌ Error: {e}")

    finally:
        if device:
            print("🔌 Disconnecting...")
            await device.disconnect()
            print("✓ Disconnected\n")


async def main():
    """Main entry point."""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║          EASYWAVE BIDI DEVICE LEARNING WITH GATEWAY SERIAL                 ║
║                                                                            ║
║ Demonstrates how to:                                                       ║
║ 1. Load gateway serial number from RX11                                    ║
║ 2. Configure filter with gateway serial                                    ║
║ 3. Learn new Bidi device                                                   ║
║ 4. Receive device type and serial number                                   ║
║                                                                            ║
║ RX11 is required - RX09 does not support Bidi protocol                     ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

    # Run device pairing workflow
    await ewb_pair_and_learn_device()

    # Uncomment to run state listener
    # await ewb_listen_state_changes()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nProgram interrupted.\n")
