#!/usr/bin/env python3
"""Test device for RX09 (ASCII Text Protocol - Different Protocol Family).

This example demonstrates:
- Creating an RX09 device (completely different protocol)
- ASCII text-based communication (vs binary RxModule)
- RX09-specific functions (11 functions vs 25 for RxModule)
- Limited capability (Easywave Basic only, no Bidi, no Secwave)
- Serial communication at 57600 baud
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from easywave_rx_module.registry import DeviceFactory
from easywave_rx_module.protocols.rx09 import RX09Device

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOGGER = logging.getLogger(__name__)


def test_rx09() -> None:
    """Test RX09 device with ASCII text protocol."""
    print("\n" + "="*80)
    print("🧪 RX09 Test Device (Different Protocol Family - ASCII Text)")
    print("="*80 + "\n")

    try:
        # Create RX09 device
        print("📱 Creating RX09 device...")
        device = DeviceFactory.create("RX09", port="/dev/ttyUSB1")
        print(f"✓ Device created: {device.DEVICE_TYPE}\n")

        # Get device info
        print("ℹ️  Device Information:")
        info = device.get_device_info()
        for key, value in sorted(info.items()):
            print(f"   {key:20} {value}")
        print()

        # Display protocol differences
        print("📊 Protocol Family Comparison:")
        print("""
        ┌─────────────────────┬──────────────┬──────────────┐
        │ Feature             │   RxModule   │    RX09      │
        ├─────────────────────┼──────────────┼──────────────┤
        │ Protocol Type       │ Binary       │ ASCII Text   │
        │ Baudrate            │ 38400/9600   │ 57600        │
        │ Frame Format        │ Binary SOP   │ CSV with CR  │
        │ Commands            │ 25 functions │ 11 functions │
        │ EasyWave Basic      │ ✓            │ ✓            │
        │ EasyWave Bidi       │ ✓            │ ✗            │
        │ Secwave             │ ✓            │ ✗            │
        │ Devices             │ RX11,RX21-25 │ RX09         │
        └─────────────────────┴──────────────┴──────────────┘
        """)

        # Get available functions
        print("📋 RX09 Available Functions (11 total):")
        functions = device.get_available_functions()
        
        print(f"   System Functions:")
        sys_funcs = ['ping', 'get_device_id', 'query_positions']
        for func in sys_funcs:
            if func in functions:
                print(f"      • {func:30} - {functions[func]}")
        
        print(f"\n   Position Management:")
        pos_funcs = ['read_position_data']
        for func in pos_funcs:
            if func in functions:
                print(f"      • {func:30} - {functions[func]}")
        
        print(f"\n   Transmission:")
        tx_funcs = ['send_telegramm', 'receive_telegramm']
        for func in tx_funcs:
            if func in functions:
                print(f"      • {func:30} - {functions[func]}")
        
        print(f"\n   Status & Control:")
        status_funcs = ['query_echo', 'set_echo', 'query_led', 'set_led', 'query_button']
        for func in sorted(status_funcs):
            if func in functions:
                print(f"      • {func:30} - {functions[func]}")
        
        print(f"\n   Total: {len(functions)} RX09-specific functions\n")

        # Show protocol specifics
        print("🔧 Protocol Details:")
        print(f"   • Commands: Comma-separated ASCII text")
        print(f"   • Terminator: CR (0x0D)")
        print(f"   • Format: COMMAND,PARAM1,PARAM2,...")
        print(f"   • Responses: 'OK' / 'ERROR' or data (e.g., 'ID,1234,5678')")
        print(f"   • Special Cases:")
        print(f"      - Escape sequence: \\ for comma and backslash")
        print(f"      - Hex values: 22-bit serial numbers, positions")
        print(f"      - Button codes: 'A', 'B', 'C', 'D'")
        print()

        # Test ping
        print("🔍 Testing device connection...")
        try:
            result = device.ping_request(timeout=5.0)
            if result:
                print(f"✓ Device ping successful")
            else:
                print(f"⚠️  Device ping timeout (device not connected)")
        except Exception as e:
            print(f"⚠️  Device not connected: {e}")

        # Show example commands
        print("\n📝 Example RX09 Commands:")
        print("""
        # Query device ID
        ID?
        Response: ID,VENDOR_ID,DEVICE_ID,VERSION

        # Query number of positions
        GETP?
        Response: GETP,NUM_POSITIONS

        # Read position data
        RDP?,POSITION
        Response: RDP,POSITION,SERIAL_NUMBER

        # Send telegramm
        TXP,POSITION,BUTTON
        Response: OK or ERROR

        # Receive telegramm (unsolicited)
        Response: REC,SERIAL_NUMBER,BUTTON

        # LED control
        LED,ON|OFF
        Response: OK or ERROR

        # ECHO control
        ECHO,ON|OFF
        Response: OK or ERROR
        """)

        print("\n" + "="*80)
        print("✓ RX09 Test Device ready (ASCII Text Protocol)")
        print("="*80 + "\n")

    except ValueError as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_rx09()
