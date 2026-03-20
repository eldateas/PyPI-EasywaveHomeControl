#!/usr/bin/env python3
"""Master test suite for all EASYWAVE device families.

This script demonstrates:
- All supported device types (RX11, RX21, RX22, RX25, RX09)
- Both protocol families (RxModule and RX09)
- Device factory pattern with variants
- Protocol capabilities comparison
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from easywave_rx_module.registry import DeviceFactory


def print_device_comparison() -> None:
    """Print comparison of all device types."""
    print("\n" + "="*100)
    print("📊 EASYWAVE Device Families Comparison")
    print("="*100 + "\n")

    # Collect device info
    devices_info = {
        "RX11-EW": {
            "port": "/dev/ttyUSB0",
            "family": "RxModule",
            "protocol": "Binary",
        },
        "RX21-EW": {
            "port": "/dev/ttyAMA0",
            "family": "RxModule",
            "protocol": "Binary",
        },
        "RX22-DEV": {
            "port": "/dev/ttyAMA1",
            "family": "RxModule",
            "protocol": "Binary",
        },
        "RX25-EW": {
            "port": "/dev/ttyUSB2",
            "family": "RxModule",
            "protocol": "Binary",
        },
        "RX09": {
            "port": "/dev/ttyUSB1",
            "family": "RX09",
            "protocol": "ASCII Text",
        },
    }

    # Table header
    print(f"{'Device':<12} {'Family':<12} {'Protocol':<15} {'Baudrate':<10} {'Variants':<15} {'Functions':<10}")
    print("-" * 100)

    # Table rows
    for device_id, info in devices_info.items():
        try:
            device = DeviceFactory.create(device_id, port=info["port"])
            dev_info = device.get_device_info()
            functions_count = len(device.get_available_functions())
            
            # Get variants for this device type
            variants_dict = DeviceFactory.get_device_variants()
            device_type = device_id.split("-")[0]
            variants = variants_dict.get(device_type, [])
            variants_str = ", ".join(variants[:3])
            if len(variants) > 3:
                variants_str += f", +{len(variants)-3}"
            
            print(f"{device_id:<12} {info['family']:<12} {info['protocol']:<15} "
                  f"{dev_info['baudrate']:<10} {variants_str:<15} {functions_count:<10}")
        except Exception as e:
            print(f"{device_id:<12} Error creating device: {e}")

    print()


def print_protocol_features() -> None:
    """Print protocol feature comparison."""
    print("="*100)
    print("🔄 Protocol Family Features")
    print("="*100 + "\n")

    print("""
    RXMODULE FAMILY (Binary Protocol)
    ─────────────────────────────────────────────────────────────────────────────────────
    • Devices: RX11-USB, RX21/RX22/RX25-Serial
    • Protocol: Binary with byte-stuffing (0x80-0x82 prefix)
    • Baudrates: 38400 (RX11, RX25), 9600 (RX21, RX22)
    • Frame: SOP(0x81) + DATA + EOP(0x82)
    • Request Pipeline: Up to 3 concurrent in-flight requests
    • Error Handling: 20+ error codes with exponential backoff
    • Health Monitoring: 30-second interval with 60-second startup tolerance
    • Protocol Variants: BASIC, EW (Standard), DEV (Developer), PRO (Professional)
    
    Function Categories (25 total):
    ├─ System (3):      ping, query_hw_version, query_fw_version
    ├─ EW Basic (6):    get_fd_serial, rcv_button, send_cmd, rcv_ex, loops
    ├─ EW Bidi (9):     add_filter, remove_filter, join, state management, learning
    └─ Secwave (7):     learn, query, stat, delete, reply, userdata

    
    RX09 FAMILY (ASCII Text Protocol)
    ─────────────────────────────────────────────────────────────────────────────────────
    • Devices: RX09-USB (Easywave Basic only)
    • Protocol: ASCII text, comma-separated, CR-terminated
    • Baudrate: 57600 (fixed)
    • Frame: COMMAND,PARAM1,PARAM2,...<CR>
    • Escape: \\ for backslash, \\, for comma
    • Response: "OK"/"ERROR" or data (e.g., "ID,1234,5678")
    • Simplicity: No pipelining, single request/response
    • Limitations: NO Bidi, NO Secwave (Basic Easywave only)
    
    Function Categories (11 total):
    ├─ System (1):      ping (implicit via ID?)
    ├─ Device ID (1):   get_device_id
    ├─ Positions (2):   query_positions, read_position_data
    ├─ Transmit (2):    send_telegramm, receive_telegramm
    └─ Status (5):      echo, led, button queries/controls
    """)

    print("\n")


def main() -> None:
    """Run master test suite."""
    print("\n" + "="*100)
    print("🚀 EASYWAVE RX Module - Multi-Family Protocol Test Suite")
    print("="*100)
    print()

    # Print device comparison
    print_device_comparison()

    # Print protocol features
    print_protocol_features()

    # Print registry info
    print("="*100)
    print("📋 Device Registry Status")
    print("="*100 + "\n")

    supported_devices = DeviceFactory.get_supported_devices()
    print(f"Total supported device IDs: {len(supported_devices)}\n")

    variants = DeviceFactory.get_device_variants()
    print("Device Types and Variants:")
    for device_type in sorted(variants.keys()):
        variant_list = variants[device_type]
        print(f"  • {device_type}: {', '.join(sorted(variant_list))}")

    print("\n" + "="*100)
    print("✓ Test suite configured. Run individual tests:")
    print("="*100)
    print("""
    $ python examples/test_rx11.py    # Test RX11 USB transceiver (RxModule)
    $ python examples/test_rx22.py    # Test RX22 Serial module (RxModule)
    $ python examples/test_rx09.py    # Test RX09 ASCII protocol (Different family)
    """)


if __name__ == "__main__":
    main()
