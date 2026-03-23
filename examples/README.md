# Examples

This directory contains example scripts demonstrating how to use the easywave-rx-module library.

All examples use the **Async API** with the new unified `.create()` factory method.

## Overview

| Example | Devices | Use Case | Key Features |
|---------|---------|----------|--------------|
| **ew_send_receive_example.py** | RX11, RX09 | Send commands to gateways, receive button presses | Gateway discovery, EW_SEND_CMD, EW_RCV, error handling |
| **ewb_pairing_example.py** | RX11 | Learn new Easywave Bidi devices | Join device, device state query, paired device management |
| **ha_integration_full_example.py** | RX11, RX09 | Home Assistant integration pattern | Background listening, event callbacks, connection management |

## Running the Examples

### Prerequisites

```bash
# Install the library (if not already installed)
pip install easywave-rx-module

# Or from source:
cd ..
pip install -e .
```

### ew_send_receive_example.py

Demonstrates Easywave Basic (EW) send and receive for both RX11 and RX09 devices.

```bash
python ew_send_receive_example.py
```

**For RX11:**
```python
async def ew_send_receive_rx11() -> None:
    device = await RX11Device.create(port="/dev/ttyUSB0")
    
    # Step 1: Discover gateways
    for i in range(10):
        result, gateway = await device.ew_get_fd_serial_request(index=i)
        if result == RX11Device.ErrorCode.SUCCESS:
            print(f"Gateway: {gateway.hex()}")
    
    # Step 2: Send command to gateway
    result = await device.ew_send_cmd_request(gateway=gateway, button=0)
    
    # Step 3: Receive button response
    result, info_type, transmitter, info_data = await device.ew_rcv_button_request(timeout=30.0)
```

**For RX09:**
```python
async def ew_send_receive_rx09() -> None:
    device = await RX09Device.create(port="/dev/ttyUSB1")
    
    # RX09 only supports receive (no send on ASCII protocol)
    # But you can listen for spontaneous button presses
    result, serial_number, button_code = await device.receive_telegramm(timeout=30.0)
```

**Shows:**
- Unified `.create()` factory method
- Device-specific ErrorCode enums
- Gateway discovery (RX11)
- Send and receive workflows
- Error handling with specific error codes
- Proper `await device.disconnect()` cleanup

### ewb_pairing_example.py

Demonstrates Easywave Bidi (EWB) device pairing workflow for RX11.

```bash
python ewb_pairing_example.py
```

**Key Features:**
```python
device = await RX11Device.create(port="/dev/ttyUSB0")

# Step 1: Learn new device (enter pairing mode)
result, receiver = await device.ewb_join_device_request(
    transmitter_serial=transmitter_bytes
)

# Step 2: Query learned device state
result, mode, state = await device.ewb_query_state_request(device_id=receiver)

# Step 3: Change device state
result = await device.ewb_change_state_request(
    device_id=receiver,
    mode=state_mode,
    state=new_state
)
```

**Shows:**
- Device pairing workflow
- State queries and changes
- Device management
- Error handling

### ha_integration_full_example.py

Real-world Home Assistant integration pattern with background listening.

```bash
python ha_integration_full_example.py
```

**Architecture:**
```python
class RxModuleHA:
    """Home Assistant integration wrapper."""
    
    def __init__(self, device_class, port, event_callback):
        self.device = await device_class.create(port=port)
    
    async def start_listening(self):
        """Start background listening for button presses."""
        # Runs listener task in background
        self._listen_task = asyncio.create_task(self._listen_loop())
    
    def register_callback(self, callback):
        """Register event callback for button presses."""
        # Callbacks fired when telegrams received
```

**Shows:**
- Device lifecycle management (create, connect, disconnect)
- Background listener task
- Event callbacks for button presses
- Connection state tracking
- Error recovery
- HA-friendly architecture

**Usage:**
```python
# Setup RX11 integration
rx11 = await setup_rx11_integration(config={"port": "/dev/ttyUSB0"})
await rx11.start_listening()

# When device disconnects or error occurs:
rx11.set_disconnect_callback(on_disconnect)

# Register for button events
def on_button_event(data):
    print(f"Button {data['button']} from {data['transmitter'].hex()}")

# For RX09, register spontaneous RCV callbacks:
rx11.device.register_rcv_callback(on_button_event)
```

## API Reference Quick Guide

### Creating Devices

```python
from easywave_rx_module import RX11Device, RX21Device, RX22Device, RX25Device, RX09Device

# RxModule devices (binary protocol, 115200 baud)
device = await RX11Device.create(port="/dev/ttyUSB0", timeout=5.0)
device = await RX21Device.create(port="/dev/ttyUSB0")
device = await RX22Device.create(port="/dev/ttyUSB0")  # Raspberry Pi UART often uses RX22
device = await RX25Device.create(port="/dev/ttyUSB0")

# RX09 device (ASCII protocol, 57600 baud)
device = await RX09Device.create(port="/dev/ttyUSB1")
```

### Common Methods

```python
# Connection
await device.connect() -> bool
await device.disconnect() -> None

# Info
await device.ping_request(timeout=5.0) -> bool
await device.get_device_info() -> dict[str, Any]

# RxModule-specific
result, hw_version = await device.query_hw_version()
result, fw_version = await device.query_fw_version()

# RX09-specific
result, count = await device.query_positions()
```

### Error Handling

```python
# Check results with device-specific ErrorCode enums
if result == RX11Device.ErrorCode.SUCCESS:
    print("Success!")
elif result == RX11Device.ErrorCode.ERR_RF_TIMEOUT:
    print("RF timeout")
else:
    print(f"Error: 0x{result:02x}")

# Common error codes
# SUCCESS (0x00) - Operation completed
# ERR_RF_TIMEOUT (0x07) - No response from device
# ERR_FAILSTATE (0xFF) - Module in failure state
```

### Callbacks

```python
# Disconnect callback
device.set_disconnect_callback(on_disconnect_func)

# RCV message callbacks (RX09 only)
device.register_rcv_callback(on_message_func)
device.unregister_rcv_callback(on_message_func)
device.clear_rcv_callbacks()
```

## Common Patterns

### Timeout Handling

```python
try:
    # ew_rcv_button_request with timeout
    result, info_type, transmitter, info_data = await device.ew_rcv_button_request(
        timeout=30.0  # 30 seconds
    )
except asyncio.TimeoutError:
    print("No button press received within 30 seconds")
```

### Indefinite Waiting (RCV functions only)

```python
# RCV functions support indefinite waiting
result, info_type, transmitter, info_data = await device.ew_rcv_button_request(
    timeout=None  # Wait indefinitely
)
```

### Background Listening

```python
# Start listening in background
listen_task = asyncio.create_task(listen_loop())

async def listen_loop():
    while True:
        try:
            result, info_type, transmitter, info_data = await device.ew_rcv_button_request(
                timeout=None  # Indefinite wait in background
            )
            if result == RX11Device.ErrorCode.SUCCESS:
                print(f"Button pressed on {transmitter.hex()}")
        except asyncio.CancelledError:
            break

# Later, cancel the task
listen_task.cancel()
```

## Type Safety

All examples pass Pylance strict-mode validation:

```bash
pylance --mode=strict examples/*.py
```

This ensures:
- All generic types are properly specified
- No "Unknown" types in IDE
- Type checking catches errors early

## Troubleshooting

### Port not found

```bash
# List available serial ports
python -c "import serial.tools.list_ports; print([p.device for p in serial.tools.list_ports.comports()])"

# Linux
ls -la /dev/ttyUSB* /dev/ttyAMA*

# macOS
ls -la /dev/tty.* /dev/cu.*
```

### Permission denied

```bash
# Linux: add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and log back in for changes to take effect
```

### Device not responding

```python
# Check if device is present
connected = await device.ping_request(timeout=3.0)
if not connected:
    print(f"Device not responding. Last error: {device.last_error}")
```

## Further Reading

See [README.md](../README.md) for:
- API documentation
- Protocol details
- Error codes reference
- Installation instructions

### ew_send_receive_example.py

**NEW:** RX11 & RX09 example showing Easywave send and receive workflow.

```bash
python ew_send_receive_example.py
```

**Shows:**
- RX11 (primary) and RX09 (secondary) implementation
- Complete workflow: Get gateways → Send command → Receive response
- EW_GET_FD_SERIAL - Discover Easywave gateways
- EW_SEND_CMD - Send command to a gateway
- EW_RCV_BUTTON - Wait for button response

**Key Features:**
- Device-specific implementations (RX11 has send, RX09 is receive-only)
- Gateway discovery and selection
- Timeout handling for responses
- Error code interpretation

**RX11 Capabilities:** Send commands, full bidirectional communication
**RX09 Capabilities:** Receive buttons, basic devices

### ewb_pairing_example.py

**NEW:** RX11 example for learning new Easywave Bidi devices.

```bash
python ewb_pairing_example.py
```

**Shows:**
- RX11 Bidi-capable gateway support
- Complete device learning workflow:
  1. Discover Bidi gateways (EWB_GET_FD_SERIAL)
  2. Add learning filter (EWB_ADD_NFILTER)
  3. Learn new device (EWB_JOIN_DEVICE)
  4. Control device state (EWB_CHANGE_STATE)
  5. Listen for state changes (EWB_RCV)
- Background listening for state changes
- Timeout-based and no-timeout modes

**Key Features:**
- Device pairing workflow
- Learning mode activation
- State change monitoring
- RX11 specific (requires Bidi-capable gateway)

**Note:** Only RX11 supports Easywave Bidi protocol. RX09, RX21, RX22, RX25 
do not support EWB methods.

### ha_integration_full_example.py

**NEW:** Complete Home Assistant integration pattern for RX11 and RX09.

```bash
python ha_integration_full_example.py
```

**Shows:**
- `RxModuleHA` class for HA service integration
- Separate setup for RX11 and RX09
- Background listening task management
- Event callbacks for button presses
- Connection lifecycle management
- Graceful shutdown handling

**Key Features:**
- Single device or multiple device setups
- Background listening (no blocking)
- Event callbacks with timestamps
- Automatic device initialization
- Error recovery and reconnection patterns
- Home Assistant event bus integration pattern

**Use Cases:**
- Long-running HA services (days/weeks of listening)
- Multiple receiver types in same setup
- Clean integration with HA's async event loop
- No polling, minimal resource usage

This is the recommended pattern for creating a full Home Assistant
custom component integrating Easywave receivers.

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

## Comprehensive Examples by Use Case

### Easywave Standard (EW) Protocol

For standard Easywave devices (gateways, switches):
- `ew_send_receive_example.py` - Send commands and receive button responses
  - RX11: Full bidirectional (send + receive)
  - RX09: Receive only

### Easywave Bidi (EWB) Protocol

For Easywave Bidi-capable devices:
- `ewb_rcv_example.py` - Receive Bidi telegrams with no timeout
- `ewb_pairing_example.py` - Learn and manage Bidi devices (RX11 only)

### Home Assistant Integration

Ready-to-use HA integration patterns:
- `ha_integration_full_example.py` - Complete service integration (RX11 + RX09)
- `ha_integration_example.py` - Entity-based integration

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

## Timeout Strategies for Integration Services

The `ewb_rcv_example.py` demonstrates techniques for services that need to listen
for occasional telegrams without blocking. This is typical in Home Assistant where
you want to respond to user actions that might take minutes, hours, or days.

### Timeout Strategies

**Short Timeout (quick response, polling):**
```python
result, ... = await device.ew_rcv_button_request(timeout=10.0)  # 10 seconds
# Then loop and call again
```
Use for: Interactive applications, checking for frequent updates

**Long Timeout (no polling, single long wait):**
```python
result, ... = await device.ew_rcv_button_request(timeout=600.0)  # 10 minutes
```
Use for: Occasional checks, less frequent updates

**NO Timeout (unlimited, waits forever):**
```python
result, ... = await device.ewb_rcv_request(timeout=None)  # Wait indefinitely!
```
Use for: Home Assistant integrations, long-running services

**Continuous Loop (multiple events):**
```python
while True:
    result, ... = await device.ewb_rcv_request(timeout=None)
    if result == ErrorCode.SUCCESS:
        # Process telegram
        pass
```
Use for: Listening for multiple telegrams in sequence

### Advantages of NO_TIMEOUT (timeout=None)

- **No CPU overhead** - Device waits cleanly, no polling loop
- **Responsive** - Telegram is processed as soon as it arrives
- **Clean shutdown** - Can interrupt with Ctrl+C or task cancellation
- **Scalable** - Can run many devices concurrently without blocking event loop
- **Perfect for HA** - Integrate naturally with Home Assistant's async design

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
