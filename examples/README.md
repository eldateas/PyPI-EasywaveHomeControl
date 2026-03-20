# Examples and Test Devices

This directory contains example scripts and test devices demonstrating how to use the easywave-rx-module library.

## Multi-Family Protocol Test Suite

The library supports two completely different protocol families. Use these test devices to verify your setup:

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
- 38400 baud
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
- 9600 baud (serial)
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
- Concurrent request pipelining (3 in-flight)
- 25 total functions
- Supports: EW Basic, EW Bidi, Secwave
- Multiple variants: BASIC, EW, DEV, PRO

### RX09 Family (ASCII Text Protocol)
**Devices:** RX09 (USB)
- Human-readable ASCII commands
- No pipelining (single request/response)
- 11 total functions
- Easywave Basic only (no Bidi/Secwave)
- Simple serial interface

## Device Factory Usage

### Creating Devices

```python
from easywave_rx_module.registry import DeviceFactory

# RxModule family (binary protocol)
rx11 = DeviceFactory.create("RX11-EW", port="/dev/ttyUSB0")
rx22 = DeviceFactory.create("RX22-DEV", port="/dev/ttyAMA0")
rx25 = DeviceFactory.create("RX25-BASIC", port="/dev/ttyUSB1")

# RX09 family (ASCII text protocol)
rx09 = DeviceFactory.create("RX09", port="/dev/ttyUSB2")
```

### Supported Device IDs

```
RxModule Family:
  RX11, RX11-BASIC, RX11-EW, RX11-DEV
  RX21, RX21-BASIC, RX21-EW, RX21-DEV
  RX22, RX22-BASIC, RX22-EW, RX22-DEV
  RX25, RX25-BASIC, RX25-EW, RX25-DEV

RX09 Family:
  RX09, RX09-BASIC
```

## basic_example.py

Simple example showing:
- Creating an RxModule instance
- Connecting to an EASYWAVE RX11 device
- Querying hardware version
- Querying firmware version
- Pinging the device
- Handling disconnects

### Usage

```bash
python basic_example.py
```

Make sure to update the port path (`/dev/ttyACM0`) to match your system.

## Running with asyncio

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
