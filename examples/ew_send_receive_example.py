#!/usr/bin/env python3
"""Example: Easywave Send & Receive with RX11 and RX09.

Demonstrates the complete Easywave workflow:
1. Get Easywave device serial numbers (gateways)
2. Send command to a device
3. Receive button press response

Works with:
- RX11 (USB Transceiver) - Primary example
- RX09 (ASCII Protocol) - Alternative implementation
"""

import asyncio
import logging
from typing import Optional

from easywave_home_control import RX09Device, RX11Device

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
_LOGGER = logging.getLogger(__name__)


async def ew_send_receive_rx11() -> None:
    """RX11: Complete Easywave send and receive workflow.
    
    Steps:
    1. Get available Easywave gateways (EW_GET_FD_SERIAL)
    2. Send command to a gateway (EW_SEND_CMD)
    3. Listen for button response (EW_RCV_BUTTON)
    """
    print("\n" + "=" * 80)
    print("RX11: Easywave Send & Receive Workflow")
    print("=" * 80 + "\n")

    device: Optional[RX11Device] = None
    try:
        # Create RX11 device
        print("📱 Creating RX11 USB Transceiver...")
        device = await RX11Device.create(
            port="/dev/ttyUSB0", timeout=5.0
        )
        print("✓ Device created and connected\n")

        # Step 1: Get available Easywave gateways
        print("📡 Step 1: Discovering Easywave gateways...")
        gateways: list[bytes] = []
        for i in range(10):  # Try first 10 entries
            result, gateway = await device.ew_get_fd_serial_request(  # type: ignore[attr-defined]
                index=i, timeout=2.0
            )
            if result == RX11Device.ErrorCode.SUCCESS and gateway != b"\x00" * 16:
                gateways.append(gateway)
                print(f"   Found gateway {i+1}: {gateway.hex()}")
            else:
                break

        if not gateways:
            print("   ⚠️  No gateways found")
            return

        # Use first gateway
        target_gateway = gateways[0]
        print(f"\n✓ Using gateway: {target_gateway.hex()}\n")

        # Step 2: Send command to gateway
        print("📤 Step 2: Sending command to gateway...")
        button = 0  # Button A
        result = await device.ew_send_cmd_request(  # type: ignore[attr-defined]
            gateway=target_gateway, button=button, timeout=5.0
        )
        if result == RX11Device.ErrorCode.SUCCESS:
            print(f"✓ Command sent successfully (Button {chr(65 + button)})\n")
        else:
            print(f"⚠️  Send failed: error {result}\n")

        # Step 3: Wait for button response
        print("📥 Step 3: Waiting for button response (30 seconds)...")
        try:
            result, info_type, transmitter, info_data = await device.ew_rcv_button_request(  # type: ignore[attr-defined]
                timeout=30.0
            )

            if result == RX11Device.ErrorCode.SUCCESS:
                print("✓ Button response received!")
                print(f"  Info Type:      0x{info_type:02X}")
                print(f"  Transmitter:    {transmitter.hex()}")
                print(f"  Info Data:      {info_data.hex()}")
            else:
                print(f"⚠️  Receive failed: error {result}")

        except asyncio.TimeoutError:
            print("⏱️  Timeout waiting for response")

    except Exception as e:
        _LOGGER.error("Error: %s", e)
        print(f"❌ Error: {e}")

    finally:
        if device:
            print("\n🔌 Disconnecting...")
            await device.disconnect()
            print("✓ Disconnected\n")


async def ew_send_receive_rx09() -> None:
    """RX09: Easywave send and receive workflow (ASCII protocol).
    
    Note: RX09 has similar functionality but uses ASCII text protocol.
    Steps are the same as RX11.
    """
    print("\n" + "=" * 80)
    print("RX09: Easywave Send & Receive Workflow (ASCII Protocol)")
    print("=" * 80 + "\n")

    device: Optional[RX09Device] = None
    try:
        # Create RX09 device
        print("📱 Creating RX09 ASCII Receiver...")
        device = await RX09Device.create(
            port="/dev/ttyUSB0", timeout=5.0
        )
        print("✓ Device created and connected\n")

        # RX09 has limited functionality compared to RX11
        # It can receive button presses but send functionality is limited
        print("📡 RX09: Waiting for button presses (no send on RX09)...")
        print("   (Send button press from Easywave transmitter)\n")

        try:
            result, info_type, transmitter, info_data = await device.ew_rcv_button_request(  # type: ignore[attr-defined]
                timeout=30.0
            )

            if result == RX09Device.ErrorCode.SUCCESS:
                print("✓ Button received!")
                print(f"  Info Type:      0x{info_type:02X}")
                print(f"  Transmitter:    {transmitter.hex()}")  # type: ignore[attr-defined]
                print(f"  Info Data:      {info_data.hex()}")  # type: ignore[attr-defined]
            else:
                print(f"⚠️  Receive failed: error {result}")

        except asyncio.TimeoutError:
            print("⏱️  Timeout waiting for button")

    except Exception as e:
        _LOGGER.error("Error: %s", e)
        print(f"❌ Error: {e}")

    finally:
        if device:
            print("\n🔌 Disconnecting...")
            await device.disconnect()
            print("✓ Disconnected\n")


async def main():
    """Main entry point."""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║              EASYWAVE SEND & RECEIVE EXAMPLES                             ║
║                                                                            ║
║ Demonstrates how to:                                                       ║
║ 1. Discover Easywave gateways                                              ║
║ 2. Send commands to devices                                                ║
║ 3. Receive button press responses                                          ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

    # Run RX11 example (primary)
    await ew_send_receive_rx11()

    # Uncomment to run RX09 example
    # await ew_send_receive_rx09()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nProgram interrupted.\n")
