# EASYWAVE Home Control

Pure Python async/await implementation for controlling EASYWAVE radio modules (RX11, RX21, RX22, RX25, RX09).

Optimized for **Home Assistant integration** with 100% non-blocking async API.

## Features

- **Pure Async/Await** - No blocking calls on event loop, optimized for Home Assistant
- **Multi-Family Support** - Binary protocol (RX11/21/22/25) + ASCII protocol (RX09)
- **High Performance** - 115200 baud communication, request pipelining
- **Robust** - Comprehensive error handling, health checks, timeout management
- **Clean API** - Unified `.create()` factory method for all devices
- **Type Hints** - Full Pylance strict-mode compliant type annotations
- **Well-Tested** - Comprehensive examples and integration patterns

## Installation

```bash
pip install easywave-home-control
```

## Quick Start

### Creating Devices

The easiest way is the `AsyncDeviceFactory` — or use the device class directly for full type safety:

```python
import asyncio
from easywave_home_control import AsyncDeviceFactory, RX11Device

async def main():
    # Option A: Factory (string-based, flexible)
    device = await AsyncDeviceFactory.create("RX11", port="/dev/ttyUSB0", timeout=5.0)

    # Option B: Device class directly (type-safe, recommended for typed code)
    # device = await RX11Device.create(port="/dev/ttyUSB0", timeout=5.0)

    try:
        # Device is now connected and ready to use
        info = await device.get_device_info()
        print(f"Device: {info}")

        # Check connectivity
        connected = await device.ping_request(timeout=3.0)
        print(f"Connected: {connected}")

        # Use device-specific methods
        result, hw_version = await device.query_hw_version()
        if result == RX11ErrorCode.SUCCESS:
            print(f"Hardware Version: {hw_version}")
    finally:
        # Always disconnect when done
        await device.disconnect()

asyncio.run(main())
```

## Device Support

### RxModule Family (Binary Protocol, 115200 baud)

| Device | Type | Functions | Features | Baudrate |
|--------|------|-----------|----------|----------|
| **RX11** | USB Transceiver | 25 | EW, Bidi, Secwave | 115200 |
| **RX21** | Serial Module | 25 | EW, Bidi, Secwave | 115200 |
| **RX22** | Serial Module | 25 | EW, Bidi, Secwave | 115200 |
| **RX25** | Serial Module | 25 | EW, Bidi, Secwave | 115200 |

### RX09 Family (ASCII Protocol, 57600 baud)

| Device | Type | Functions | Features | Baudrate |
|--------|------|-----------|----------|----------|
| **RX09** | Basic Receiver | 11 | EW Basic only | 57600 |

## Async API Documentation

### Device Classes

#### RxModule Devices (Binary Protocol, 115200 baud)

```python
from easywave_home_control import RX11Device, RX21Device, RX22Device, RX25Device

# All RxModule devices use the same interface
device = await RX11Device.create(port="/dev/ttyUSB0")

# RxModule-specific methods
result, hw_version = await device.query_hw_version()
result, fw_version = await device.query_fw_version()

# Easywave Basic (EW) functions
result, info_type, transmitter, info_data = await device.ew_rcv_button_request(timeout=30.0)
await device.ew_send_cmd_request(gateway=gateway_serial, button=0)

# Easywave Bidi (EWB) functions
result, receiver = await device.ewb_join_device_request(transmitter_serial)

# Check error codes
if result == RX11ErrorCode.SUCCESS:
    print(f"Success: {info_type}")
else:
    print(f"Error: {result}")
```

#### RX09 Device (ASCII Protocol, 57600 baud)

```python
from easywave_home_control import RX09Device

device = await RX09Device.create(port="/dev/ttyUSB0")

# RX09-specific methods
result, serial_number, button_code = await device.receive_telegramm(timeout=30.0)
result, position_count = await device.query_positions()
result = await device.send_telegramm(position=0, button_code="A")

# Check error codes
if result == RX09ErrorCode.SUCCESS:
    print("Success")
```

#### Common Methods (All Devices)

```python
# Connection management
# Note: .connect() is called automatically by .create() — only needed for direct instantiation
await device.connect() -> bool
await device.disconnect() -> None

# Device info
await device.get_device_info() -> dict[str, Any]
await device.ping_request(timeout=5.0) -> bool

# Properties (common)
device.is_connected -> bool
```

#### RxModule-Only Properties (RX11 / RX21 / RX22 / RX25)

```python
# Detailed status — one of: "connected", "disconnected", "reconnecting", "error", "hardware_error"
device.connection_status -> str
device.has_hardware_error -> bool  # True after USB disconnect or I/O error
device.state_good -> bool          # False if protocol errors have occurred
device.last_error -> str | None    # Last error message, if any
```

### Error Codes

Each device family has device-specific error code enums:

```python
# RxModule devices (RX11, RX21, RX22, RX25)
from easywave_home_control import RX11Device, RX11ErrorCode

if result == RX11ErrorCode.SUCCESS:
    print("Command successful")
elif result == RX11ErrorCode.ERR_RF_TIMEOUT:
    print("RF communication timeout")
elif result == RX11ErrorCode.ERR_FAILSTATE:
    print("Device in failure state")

# RX09 device
from easywave_home_control import RX09Device, RX09ErrorCode

if result == RX09ErrorCode.SUCCESS:
    print("Command successful")
```

### Callbacks

Register callbacks to respond to device events:

```python
def on_disconnect():
    print("Device disconnected or hardware error occurred")

device.set_disconnect_callback(on_disconnect)

# Register callback for spontaneous RCV messages (RX09 only)
def on_button_pressed(data: dict[str, Any]):
    serial = data["serial_number"]
    button = data["button_code"]
    print(f"Button {button} pressed on {serial:06X}")

device.register_rcv_callback(on_button_pressed)
```

## Examples

See the [examples/](examples/) directory for complete working examples:

- **[ew_send_receive_example.py](examples/ew_send_receive_example.py)** - Discover gateways, send commands, receive button presses (RX11 & RX09)
- **[ewb_pairing_example.py](examples/ewb_pairing_example.py)** - Easywave Bidi device pairing workflow
- **[ha_integration_full_example.py](examples/ha_integration_full_example.py)** - Home Assistant integration pattern with background listening

## Protocol Details

### RxModule Protocol (RX11/21/22/25)

Binary request/response protocol at 115200 baud with:
- Packet structure: `[SOP(0x81)] [Function+Params] [EOP(0x82)]`
- Byte stuffing for bytes in range 0x80-0x82
- Request/response IRP/ICP pairs with handles
- Timeout support (default 5.0s, RCV functions support indefinite waiting)

### RX09 Protocol (RX09)

ASCII text-based protocol at 57600 baud with:
- Comma-separated commands (e.g., `CMD,PARAM1,PARAM2`)
- CR (0x0D) line terminator
- Simple request/response matching
- Limited function set (Easywave Basic only)

## Type Hints & Validation

The library is fully typed and passes Pylance strict-mode validation:
```bash
pylance --mode=strict
```

All generic types are explicitly specified (no `Unknown` types):
- `dict[str, Any]` instead of `dict`
- `list[bytes]` instead of `list`
- `asyncio.Task[None]` instead of `asyncio.Task`

## Requirements

- Python 3.9+
- pyserial >= 3.5

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please submit issues and pull requests to the [Home Assistant repository](https://github.com/home-assistant/core).

## Support

For support, please refer to the [Home Assistant Easywave Integration](https://www.home-assistant.io/integrations/easywave) documentation.
