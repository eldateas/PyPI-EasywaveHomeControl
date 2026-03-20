# Examples and Test Devices

This directory contains example scripts and test devices demonstrating how to use the easywave-rx-module library.

## Quick Start

All examples use the **Async API** which is recommended for:
- Home Assistant integration (no blocking calls on event loop)
- Modern Python development (asyncio/await)
- Better error handling with timeouts
- Non-blocking device operations

## Async API Examples (Recommended)

### basic_example.py

Simple, clean example of the async API - a great starting point!

```bash
python basic_example.py
```

**Shows:**
- `AsyncDeviceFactory.create()` - Creates and connects device automatically
- Getting device status
- Querying hardware/firmware versions
- Device connectivity check
- Proper `await device.disconnect()` cleanup

**Key Point:** `create()` automatically calls `connect()` internally, so you only need to call `disconnect()` when done.

### async_example.py

Comprehensive async demonstration with device information and function listing.

```bash
python async_example.py
```

**Shows:**
- Complete async device creation and connection
- Device info retrieval
- Function discovery
- Ping/connectivity testing
- Available async methods documentation

### rcv_callback_example.py

RX09-specific example showing how to receive button presses asynchronously.

```bash
python rcv_callback_example.py
```

**Shows:**
- RX09 device setup
- Waiting for button telegram
- Timeout handling
- Multiple press reception loop

### ha_integration_example.py

Complete Home Assistant integration pattern.

```bash
python ha_integration_example.py
```

**Shows:**
- How to structure a HA custom component
- Async setup and teardown
- Health checks and connection management
- Entity platform integration
- Proper error handling with timeouts

This is the recommended pattern for Home Assistant custom components.

---

## Test Suites

### test_all_devices.py

Master test suite showing all 5 supported devices across 2 protocol families.

```bash
python test_all_devices.py
```

**Tests:**
- RX11 (USB Transceiver)
- RX21 (Serial Module)
- RX22 (Serial Module)
- RX25 (Serial Module)
- RX09 (ASCII Protocol)

### test_async_api.py

Quick test of async API (Home Assistant compatibility check).

```bash
python test_async_api.py
```

### test_rx09.py, test_rx11.py, test_rx22.py

Device-specific tests for individual protocols.

```bash
python test_rx09.py
python test_rx11.py
python test_rx22.py
```

---

## Supported Devices

| Device | Protocol | Features |
|--------|----------|----------|
| RX09 | ASCII | Basic receiver, button presses |
| RX11 | Binary | USB transceiver (115200 bps) |
| RX21 | Binary | Serial module (115200 bps) |
| RX22 | Binary | Serial module (115200 bps) |
| RX25 | Binary | Serial module (115200 bps) |

---

## Connection Parameters

All examples use these default connection parameters:

```python
device = await AsyncDeviceFactory.create(
    "RX22",                    # Device type
    port="/dev/ttyUSB0",       # Serial port
    timeout=5.0                # Default timeout
)
```

**Linux:** `/dev/ttyUSB0`, `/dev/ttyAMA0` (Raspberry Pi)
**Windows:** `COM1`, `COM3`, etc.
**macOS:** `/dev/tty.usbserial-*`

---

## Error Handling

All async methods support timeout handling:

```python
try:
    result, data = await device.query_hw_version(timeout=5.0)
    if result == ErrorCode.SUCCESS:
        print(f"Hardware: {data.hex()}")
except asyncio.TimeoutError:
    print("Timeout waiting for device")
except Exception as e:
    print(f"Error: {e}")
finally:
    await device.disconnect()
```

---

## Running Examples

### Prerequisites

```bash
pip install easywave-rx-module
python3 -m pip install --upgrade pip
```

### Execute

```bash
cd examples/

# Run basic example
python3 basic_example.py

# Run with logging
PYTHONUNBUFFERED=1 python3 basic_example.py 2>&1 | tee output.log
```

### Troubleshooting

If you get `No module named 'serial'`:
```bash
pip install pyserial
```

If you get port permission denied:
```bash
# Linux - add user to dialout group
sudo usermod -a -G dialout $USER
# Then logout and login again

# Or run with sudo
sudo python3 basic_example.py
```

---

## Integration with Home Assistant

The library is designed specifically for Home Assistant integration:

1. Pure async API (no blocking calls)
2. Timeout support on all operations
3. Graceful error handling
4. Resource cleanup on disconnect

See `ha_integration_example.py` for the recommended pattern.

**Output:**
- Device comparison table (baudrate, variants, function count)
- Protocol family feature overview
- Device registry information

### test_rx11.py

Test device for **RX11 (USB Transceiver - RxModule family)**

```bash
python test_rx11.py
```

**Features:**
- 25 functions (EasyWave Basic, Bidi, Secwave)
- Binary protocol with request pipelining
- **115200 baud** (all RxModule devices)
- USB connection
- Health monitoring (30-second interval)

### test_rx22.py

Test device for **RX22 (Serial Module - RxModule family)**

```bash
python test_rx22.py
```

**Features:**
- Tests both EW (standard) and DEV (developer) variants
- 25 functions same as RX11
- Binary protocol with byte-stuffing
- **115200 baud** (all RxModule devices)
- Serial UART connection
- Configurable timeout

### test_rx09.py

Test device for **RX09 (Different Protocol Family - ASCII Text)**

```bash
python test_rx09.py
```

**Key Differences:**
- Only 11 functions (Easywave Basic only - no Bidi, no Secwave)
- ASCII text protocol (comma-separated commands, CR terminator)
- 57600 baud (fixed)
- Simple single-request/response model
- LED, ECHO, BUTTON control via ASCII commands
- Position/serial management for 22-bit Easywave codes

## Protocol Families

### RxModule Family (Binary Protocol)
**Devices:** RX11 (USB), RX21/RX22/RX25 (Serial)
- Binary, byte-stuffed packets
- Concurrent request pipelining
- **115200 baud (all devices)**
- 25 total functions
- Supports: EW Basic, EW Bidi, Secwave

### RX09 Family (ASCII Text Protocol)
**Devices:** RX09 (USB)
- Human-readable ASCII commands
- No pipelining (single request/response)
- **57600 baud (fixed)**
- 11 total functions
- Easywave Basic only (no Bidi/Secwave)
- Simple serial interface

## Async Device Factory Usage

### Creating Devices (Async)

```python
from easywave_rx_module import AsyncDeviceFactory

async def example():
    # RxModule family (115200 baud)
    rx11 = await AsyncDeviceFactory.create("RX11", port="/dev/ttyUSB0")
    rx22 = await AsyncDeviceFactory.create("RX22", port="/dev/ttyAMA0")
    rx25 = await AsyncDeviceFactory.create("RX25", port="/dev/ttyUSB1")
    
    # RX09 family (57600 baud)
    rx09 = await AsyncDeviceFactory.create("RX09", port="/dev/ttyUSB2")
    
    # Always disconnect when done!
    await rx11.disconnect()
    await rx22.disconnect()
    await rx25.disconnect()
    await rx09.disconnect()
```

### Supported Device IDs

```
RxModule Family (115200 baud):
  RX11, RX21, RX22, RX25

RX09 Family (57600 baud):
  RX09, RX09-BASIC
```

## Legacy: basic_example.py (Deprecated - Old Sync API)

For async applications, you can use the threading model and integrate with asyncio:

```python
import asyncio
from easywave_rx_module import RxModule

async def main():
    rx = RxModule(port="/dev/ttyACM0")
    
    if not rx.connect():
        print("Connection failed")
        return
    
    # Run query in executor to avoid blocking
    loop = asyncio.get_event_loop()
    result, hw_ver = await loop.run_in_executor(
        None, 
        lambda: rx.query_hw_version(timeout=5.0)
    )
    
    print(f"Hardware: {hw_ver.hex()}")
    
    rx.dispose()

asyncio.run(main())
```
