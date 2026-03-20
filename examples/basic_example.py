#!/usr/bin/env python3
"""Simple example of using the easywave-rx-module library."""

from easywave_rx_module import RxModule, ErrorCode


def main():
    """Main example function."""
    # Create module instance
    rx = RxModule(port="/dev/ttyACM0")

    # Set disconnect callback
    def on_disconnect():
        print("Device disconnected!")

    rx.set_disconnect_callback(on_disconnect)

    # Connect to device
    if not rx.connect():
        print(f"Failed to connect: {rx.last_error}")
        return

    print(f"Connected: {rx.is_connected}")
    print(f"Status: {rx.connection_status}")

    # Query hardware version
    result, hw_ver = rx.query_hw_version(timeout=5.0)
    if result == ErrorCode.SUCCESS:
        print(f"Hardware version: {hw_ver.hex()}")
    else:
        print(f"Hardware query failed: {result}")

    # Query firmware version
    result, major, minor, incomplete = rx.query_fw_version(timeout=5.0)
    if result == ErrorCode.SUCCESS:
        incomplete_str = " (incomplete)" if incomplete else ""
        print(f"Firmware version: {major}.{minor}{incomplete_str}")
    else:
        print(f"Firmware query failed: {result}")

    # Ping device
    result = rx.ping(duration=5)
    if result == ErrorCode.SUCCESS:
        print("Ping successful")
    else:
        print(f"Ping failed: {result}")

    # Cleanup
    rx.dispose()
    print("Disconnected")


if __name__ == "__main__":
    main()
