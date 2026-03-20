#!/usr/bin/env python3
"""Test device for RX22 (Serial Module - RxModule family).

This example demonstrates:
- Creating an RX22 device with DeviceFactory
- Device initialization with standard configuration
- Variant selection (EW and DEV)
- Protocol capabilities
- Serial port configuration
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from easywave_rx_module.registry import DeviceFactory

# Setup logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
_LOGGER = logging.getLogger(__name__)


def test_rx22_variant(variant: str) -> None:
    """Test RX22 device with specified variant."""
    print("\n" + "=" * 80)
    print(f"🧪 RX22 Test Device - {variant.upper()} Variant")
    print("=" * 80 + "\n")

    try:
        # Create RX22 device with variant
        device_id = f"RX22-{variant.upper()}"
        print(f"📱 Creating {device_id} device...")
        device = DeviceFactory.create(device_id, port="/dev/ttyAMA0", timeout=10.0)
        print(f"✓ Device created: {device.DEVICE_TYPE}\n")

        # Get device info
        print("ℹ️  Device Configuration:")
        info = device.get_device_info()
        print("   Hardware:          RX22 (Serial Module)")
        print(f"   Baudrate:          {info['baudrate']} baud")
        print(f"   Variant:           {info['variant'].upper()}")
        print(f"   Connection Type:   {info['connection_type']}")
        print()

        # Get available functions
        print("📋 Available Functions:")
        functions = device.get_available_functions()

        # Group functions by module
        ew_funcs = [k for k in functions.keys() if k.startswith("ew_")]
        ewb_funcs = [k for k in functions.keys() if k.startswith("ewb_")]
        sec_funcs = [k for k in functions.keys() if k.startswith("sec_")]

        print(f"   EasyWave Basic:    {len(ew_funcs)} functions")
        print(f"   EasyWave Bidi:     {len(ewb_funcs)} functions")
        print(f"   Secwave:           {len(sec_funcs)} functions")
        print("   System:            3 functions (ping, query_hw_version, query_fw_version)")
        print(f"   Total:             {len(functions)} functions\n")

        # Test ping
        print("🔍 Testing connection...")
        try:
            result = device.ping_request(timeout=5.0)
            if result:
                print("✓ Device ping successful")
            else:
                print("⚠️  Device ping timeout (device not connected)")
        except Exception as e:
            print(f"⚠️  Device not connected: {e}")

        print()

    except ValueError as e:
        print(f"❌ Error: {e}")


def test_all_rx22_variants() -> None:
    """Test all RX22 variants."""
    print("\n" + "=" * 80)
    print("🧪 RX22 Test Devices (All Variants)")
    print("=" * 80)

    variants = ["EW", "DEV"]

    for variant in variants:
        test_rx22_variant(variant)

    print("\n" + "=" * 80)
    print("✓ RX22 Test Devices configured for serial communications")
    print("=" * 80 + "\n")
    print("""
Next Steps:
1. Connect RX22 to serial port /dev/ttyAMA0
2. Run: test_rx11.py for USB device testing
3. Run: test_rx09.py for ASCII protocol testing
    """)


if __name__ == "__main__":
    test_all_rx22_variants()
