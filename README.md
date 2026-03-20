# EASYWAVE RX11 Hardware Communication Library

Pure Python implementation of the RxModule protocol for communicating with EASYWAVE RX11 USB transceivers.

## Features

- **Pure Python** - No C extensions, cross-platform compatible
- **Async Ready** - Thread-safe design, callbacks for state changes
- **Robust** - Comprehensive error handling, health checks, automatic reconnection support
- **Protocol Implementation** - Full RxModule packet encoding/decoding with byte stuffing
- **Health Monitoring** - Connection health checks, hardware error detection
- **Clean API** - Easy-to-use interface for hardware/firmware version queries and device control

## Installation

```bash
pip install easywave-rx-module
```

## Quick Start

```python
from easywave_rx_module import RxModule

# Create module instance
rx = RxModule(port="/dev/ttyACM0")

# Connect to device
if not rx.connect():
    print("Failed to connect")
    exit(1)

# Query hardware version
result, hw_ver = rx.query_hw_version(timeout=5.0)
print(f"Hardware version: {hw_ver}")

# Query firmware version
result, major, minor, incomplete = rx.query_fw_version(timeout=5.0)
print(f"Firmware: {major}.{minor}")

# Cleanup
rx.dispose()
```

## API Documentation

### RxModule Class

Main class for communicating with EASYWAVE RX11 devices.

#### Constructor

```python
RxModule(port: str, baudrate: int = 115200)
```

- **port**: Serial port path (e.g., "/dev/ttyACM0" on Linux, "COM3" on Windows)
- **baudrate**: Serial baudrate (default: 115200)

#### Connection Methods

```python
connect() -> bool
```
Connect to the RX11 device. Returns `True` on success.

```python
dispose()
```
Disconnect and cleanup resources. Safe to call multiple times.

#### Query Methods

```python
query_hw_version(timeout: float = 5.0) -> tuple[int, bytes]
```
Query hardware version. Returns error code and hardware version bytes.

```python
query_fw_version(timeout: float = 5.0) -> tuple[int, int, int, bool]
```
Query firmware version. Returns error code, major version, minor version, and incomplete flag.

```python
ping(duration: int = 5) -> int
```
Ping the device. Returns error code.

#### Properties

```python
is_connected: bool
```
Check if device is connected and healthy.

```python
connection_status: str
```
Get detailed connection status ("connected", "disconnected", "reconnecting", "hardware_error", "error").

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
