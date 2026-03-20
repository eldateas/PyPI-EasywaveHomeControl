#!/usr/bin/env python3
"""Test device for RX11 (USB Transceiver - RxModule family).

This example demonstrates:
- Creating an RX11 device with DeviceFactory
- Device initialization and info retrieval
- Basic protocol operations
- Error handling
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from easywave_rx_module.registry import DeviceFactory

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOGGER = logging.getLogger(__name__)


def test_rx11() -> None:
    """Test RX11 device with EW variant."""
    print("\n" + "="*80)
    print("🧪 RX11 Test Device (RxModule Family - USB Transceiver)")
    print("="*80 + "\n")

    try:
        # Create RX11-EW device
        print("📱 Creating RX11-EW device...")
        device = DeviceFactory.create("RX11-EW", port="/dev/ttyUSB0")
        print(f"✓ Device created: {device.DEVICE_TYPE}\n")

        # Get device info
        print("ℹ️  Device Information:")
        info = device.get_device_info()
        for key, value in sorted(info.items()):
            print(f"   {key:20} {value}")
        print()

        # Get available functions
        print("📋 Available Functions (RxModule - 25 functions):")
        functions = device.get_available_functions()
        
        # Group functions by module
        ew_funcs = [k for k in functions.keys() if k.startswith('ew_')]
        ewb_funcs = [k for k in functions.keys() if k.startswith('ewb_')]
        sec_funcs = [k for k in functions.keys() if k.startswith('sec_')]
        sys_funcs = [k for k in functions.keys() if k in ['ping', 'query_hw_version', 'query_fw_version']]
        
        print(f"   System Functions ({len(sys_funcs)}):")
        for func in sorted(sys_funcs):
            print(f"      • {func}")
        
        print(f"\n   EasyWave Basic Functions ({len(ew_funcs)}):")
        for func in sorted(ew_funcs):
            print(f"      • {func}")
        
        print(f"\n   EasyWave Bidi Functions ({len(ewb_funcs)}):")
        for func in sorted(ewb_funcs):
            print(f"      • {func}")
        
        print(f"\n   Secwave Functions ({len(sec_funcs)}):")
        for func in sorted(sec_funcs):
            print(f"      • {func}")

        print(f"\n   Total: {len(functions)} functions available")
        print()

        # Test ping
        print("🔍 Testing ping_request()...")
        try:
            result = device.ping_request(timeout=5.0)
            if result:
                print(f"✓ Device ping successful")
            else:
                print(f"⚠️  Device ping timeout (device not connected)")
        except Exception as e:
            print(f"⚠️  Device not connected: {e}")

        print("\n" + "="*80)
        print("✓ RX11 Test Device ready for testing")
        print("="*80 + "\n")

    except ValueError as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_rx11()
