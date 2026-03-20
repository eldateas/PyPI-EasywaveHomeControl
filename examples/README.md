# Examples and Test Devices

This directory contains example scripts and test devices demonstrating how to use the easywave-rx-module library.

## Async API Examples (Recommended)

### async_example.py

Simple, clean example of the async API.

```bash
python async_example.py
```

**Shows:**
- `AsyncDeviceFactory.create()` - Creates and connects device automatically
- Getting device information
- Pinging the device
- Listing available functions
- **Important:** Proper `await device.disconnect()` in finally block

**Key Point:** `create()` automatically calls `connect()` internally, so you only need to call `disconnect()` when done.

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

### test_all_devices.py

Master test suite showing all 5 supported devices across 2 protocol families.

```bash
python test_all_devices.py
```

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

Test device for **RX22 (Serial Module Enhanced - RxModule family)**

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
