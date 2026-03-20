# EASYWAVE RX Module Library

Pure Python async/await implementation for communicating with EASYWAVE radio modules (RX11, RX21, RX22, RX25, RX09).

Optimized for **Home Assistant integration** with 100% non-blocking async API.

## Features

- **Pure Async/Await** - No blocking calls on event loop, optimized for Home Assistant
- **Multi-Family Support** - Binary protocol (RX11/21/22/25) + ASCII protocol (RX09)
- **High Performance** - 115200 baud communication, request pipelining
- **Robust** - Comprehensive error handling, health checks, timeout management
- **Clean API** - Simple async factory pattern for device creation
- **Type Hints** - Full TypeScript-style type annotations

## Installation

```bash
pip install easywave-rx-module
```

## Important: Always Call disconnect()

The `AsyncDeviceFactory.create()` method automatically calls `connect()` internally, but **you must always call `await device.disconnect()`** when done:

```python
try:
    device = await AsyncDeviceFactory.create("RX22", port="/dev/ttyAMA0")
    # ... use device ...
finally:
    await device.disconnect()  # Always cleanup!
```

## Quick Start (Async API)

```python
import asyncio
from easywave_rx_module import AsyncDeviceFactory

async def main():
    # Create and connect to device (both in one call)
    device = await AsyncDeviceFactory.create(
        "RX22",
        port="/dev/ttyAMA0",  # Raspberry Pi UART
        timeout=5.0
    )
    
    # Get device info
    info = await device.get_device_info()
    print(f"Device: {info}")
    
    # Check connectivity
    connected = await device.ping_request(timeout=3.0)
    print(f"Connected: {connected}")
    
    # Always disconnect when done!
    await device.disconnect()

asyncio.run(main())
```

## Device Support

### RxModule Family (Binary Protocol, 115200 baud)

| Device | Type | Functions | Features | Baudrate |
|--------|------|-----------|----------|----------|
| **RX11** | USB Transceiver | 25 | EW, Bidi, Secwave | 115200 |
| **RX21** | Serial Module | 25 | EW, Bidi, Secwave | 115200 |
| **RX22** | Serial Enhanced | 25 | EW, Bidi, Secwave | 115200 |
| **RX25** | Serial High-Speed | 25 | EW, Bidi, Secwave | 115200 |

### RX09 Family (ASCII Protocol, 57600 baud)

| Device | Type | Functions | Features | Baudrate |
|--------|------|-----------|----------|----------|
| **RX09** | Basic Receiver | 11 | EW Basic only | 57600 |

## Async API Documentation

### AsyncDeviceFactory

Factory for creating async device instances.

#### Creating Devices

```python
device = await AsyncDeviceFactory.create(
    device_id="RX22",        # Device type
    port="/dev/ttyAMA0",      # Serial port
    timeout=5.0,              # Default timeout
    variant="EW"              # Optional variant
)
```

**Supported Device IDs:**
- RxModule: `RX11`, `RX21`, `RX22`, `RX25`
- RX09: `RX09`, `RX09-BASIC`

#### Device Methods

All devices inherit from `AsyncBaseProtocol` with these methods:

```python
# Connection
await device.connect() -> bool        # Usually called automatically
await device.disconnect()              # Required: cleanup on shutdown

# Info
await device.ping_request(timeout=5.0) -> bool
await device.get_device_info()         # Returns dict with type, port, baudrate
await device.get_available_functions() # Returns dict of available functions
```

**RxModule-specific (RX11/21/22/25):**

```python
await device.query_hw_version() -> tuple[int, str]
await device.query_fw_version() -> tuple[int, str]
await device.ew_send_cmd_request(gateway_id, button) -> tuple[int, bytes]
await device.ew_rcv_button_request() -> tuple[int, bytes]
```

**RX09-specific:**

```python
await device.get_device_id()          # Device identification
await device.query_positions()        # Number of positions
await device.send_telegramm(pos, button)  # Send telegram
await device.query_led() -> bool      # LED status
await device.set_led(enabled)         # Control LED
```

```python
has_hardware_error: bool
```
Check if a hardware error occurred (e.g., USB disconnected).

```python
last_error: str | None
```
Get the last error message.

#### Callbacks

```python
set_disconnect_callback(callback: Callable[[], None] | None) -> None
```
Register a callback to be called when the device disconnects or a hardware error occurs.

### Constants

#### Error Codes

```python
from easywave_rx_module import ErrorCode

ErrorCode.SUCCESS           # 0x00
ErrorCode.ERR_RF_TIMEOUT    # 0x07 - Command timeout
ErrorCode.ERR_FAILSTATE     # 0xFF - Module in failure state
# ... and more
```

#### Function Codes

```python
from easywave_rx_module import FunctionCode

FunctionCode.MA_QUERY_HW_VER  # Hardware version query
FunctionCode.MA_QUERY_FW_VER  # Firmware version query
FunctionCode.PING_RCV         # Ping
# ... and more
```

## Protocol Details

### RxModule Protocol

The RxModule protocol is a serial-based request/response protocol used by EASYWAVE RX11 devices.

#### Packet Structure

```
[SOP] [Function | Params] [EOP]

SOP = 0x81 (Start of Packet)
EOP = 0x82 (End of Packet)
```

#### Byte Stuffing

Bytes in the range 0x80-0x82 are escaped with a prefix byte:
- Byte to stuff: `byte`
- Escaped: `0x80 (byte - 0x80)`

### Data Structures

#### IRP (I/O Request Packet)

Represents a command to be sent to the device.

#### ICP (I/O Completion Packet)

Represents a response received from the device.

#### Request

Internal structure tracking a pending request with its handle and result.

## Examples

### Monitoring Connection State

```python
from easywave_rx_module import RxModule

def on_disconnect():
    print("Device disconnected!")

rx = RxModule(port="/dev/ttyACM0")
rx.set_disconnect_callback(on_disconnect)

if rx.connect():
    print(f"Connected: {rx.is_connected}")
    print(f"Status: {rx.connection_status}")
```

### Error Handling

```python
from easywave_rx_module import RxModule, ErrorCode

rx = RxModule(port="/dev/ttyACM0")

if not rx.connect():
    print(f"Connection failed: {rx.last_error}")
    exit(1)

result, hw_ver = rx.query_hw_version()

if result == ErrorCode.SUCCESS:
    print(f"Success: {hw_ver}")
elif result == ErrorCode.ERR_RF_TIMEOUT:
    print("Request timed out")
else:
    print(f"Error: {result}")
```

## Requirements

- Python 3.9+
- pyserial >= 3.5

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please submit issues and pull requests to the [Home Assistant repository](https://github.com/home-assistant/core).

## Support

For support, please refer to the [Home Assistant Easywave Integration](https://www.home-assistant.io/integrations/easywave) documentation.
