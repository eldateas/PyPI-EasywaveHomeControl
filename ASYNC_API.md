"""# Async API Documentation

## Overview

The **Async API** is the **PRIMARY API** for Home Assistant integration. It provides non-blocking, event-loop-safe device communication suitable for use in Home Assistant and other async frameworks.

## Key Features

✅ **100% Non-Blocking**: All operations use `async/await` - no blocking calls on event loop  
✅ **thread pool based**: Synchronous device I/O runs in ThreadPoolExecutor to prevent blocking  
✅ **Home Assistant Compatible**: Follows HA async patterns and conventions  
✅ **Both Protocol families**: Works with RxModule (RX11/21/22/25) and RX09  
✅ **Proper Error Handling**: Built-in timeouts and exception handling  
✅ **Multiple Device Support**: Run multiple devices concurrently on same event loop  

## Import Structure

```python
# Primary API for Home Assistant
from easywave_rx_module import AsyncDeviceFactory, AsyncDeviceBase

# Also available:
from easywave_rx_module import (
    AsyncRxModuleDevice,  # For RX11, RX21, RX22, RX25
    AsyncRX09Device       # For RX09
)
```

## Basic Usage

### Creating a Device

```python
from easywave_rx_module import AsyncDeviceFactory

# RX22 on Raspberry Pi
device = await AsyncDeviceFactory.create(
    "RX22",
    port="/dev/ttyAMA0",
    timeout=5.0
)

# RX11 USB Transceiver
device = await AsyncDeviceFactory.create(
    "RX11",
    port="/dev/ttyUSB0"
)

# RX09 ASCII protocol
device = await AsyncDeviceFactory.create(
    "RX09",
    port="/dev/ttyUSB1"
)
```

### Using Device Methods

All methods are async and non-blocking:

```python
# Get device information
info = await device.get_device_info()
print(info)  # {'device_type': 'RX22', 'port': '/dev/ttyAMA0', ...}

# Get available functions
functions = await device.get_available_functions()

# Ping device (non-blocking!)
connected = await device.ping_request(timeout=3.0)

# Query hardware/firmware version (RxModule only)
hw_version = await device.query_hw_version()
fw_version = await device.query_fw_version()

# Disconnect gracefully
await device.disconnect()
```

## RxModule API (RX11, RX21, RX22, RX25)

### EasyWave Basic (EW) Functions

```python
# Send command to gateway
error_code, data = await device.ew_send_cmd_request(
    gateway_id=123456,
    button=0  # Button 0-3
)

# Receive button press
error_code, button_data = await device.ew_rcv_button_request()

# Get serial number at index
error_code, serial_bytes = await device.ew_get_fd_serial_request(index=0)

# Receive extended telegram
info_type, telegram = await device.ew_rcv_ex_request()
```

### EasyWave Bidi (EWB) Functions

```python
# Query device state
error_code, state = await device.ewb_query_state_request(gateway_id=123456)

# Change device state
error_code, response = await device.ewb_change_state_request(
    gateway_id=123456,
    state=1  # New state value
)

# Receive bidi telegram
error_code, telegram = await device.ewb_rcv_request()

# Get EWB serial number
error_code, serial = await device.ewb_get_fd_serial_request(index=0)
```

### Secwave (SEC) Functions

```python
# Receive secure telegram
error_code, telegram = await device.sec_rcv_request()

# Learn/program device
error_code, response = await device.sec_learn_request(
    gateway_id=123456,
    button=0
)
```

## RX09 API (ASCII Protocol)

```python
# Get device ID
result_code, id_dict = await device.get_device_id()
# Returns: (0, {'vendor_id': ..., 'device_id': ..., 'version': ...})

# Query positions
result_code, num_positions = await device.query_positions()

# Read position data
result_code, serial = await device.read_position_data(position=0)

# Send telegram
result_code, response = await device.send_telegramm(
    position=0,
    button='A'  # or 'B', 'C', 'D'
)

# Receive telegram (blocking wait)
result_code, telegram = await device.receive_telegramm(timeout=5.0)

# Echo control
result_code, enabled = await device.query_echo()
result_code, response = await device.set_echo(enabled=True)

# LED control
result_code, status = await device.query_led()
result_code, response = await device.set_led(enabled=True)

# Button status
result_code, button = await device.query_button()
```

## Home Assistant Integration Pattern

```python
from homeassistant.core import HomeAssistant
from easywave_rx_module import AsyncDeviceFactory

class EasywaveCoordinator:
    def __init__(self, hass: HomeAssistant, device_id: str, port: str):
        self.hass = hass
        self._device = None
        self._config = {"device_id": device_id, "port": port}
    
    async def async_init(self) -> bool:
        """Initialize device during HA startup."""
        try:
            self._device = await AsyncDeviceFactory.create(
                self._config["device_id"],
                port=self._config["port"]
            )
            
            # Verify device is accessible
            if not await self._device.ping_request(timeout=3.0):
                return False
            
            return True
        except Exception as e:
            _LOGGER.error("Failed to initialize: %s", e)
            return False
    
    async def async_shutdown(self) -> None:
        """Clean up during HA shutdown."""
        if self._device:
            await self._device.disconnect()
    
    async def async_send_command(self, gateway_id: int, button: int) -> bool:
        """Send command - example entity handler."""
        if not self._device:
            return False
        
        try:
            error_code, data = await self._device.ew_send_cmd_request(
                gateway_id,
                button
            )
            return error_code == 0
        except Exception:
            return False
```

## Multiple Device Management

Run multiple devices concurrently on the same event loop:

```python
# Create devices concurrently
rx22_task = AsyncDeviceFactory.create("RX22", port="/dev/ttyUSB0")
rx11_task = AsyncDeviceFactory.create("RX11", port="/dev/ttyUSB1")

rx22, rx11 = await asyncio.gather(rx22_task, rx11_task)

# Use concurrently
results = await asyncio.gather(
    rx22.ping_request(timeout=2.0),
    rx11.ping_request(timeout=2.0),
    rx22.query_hw_version(),
)

# Cleanup
await asyncio.gather(
    rx22.disconnect(),
    rx11.disconnect()
)
```

## Error Handling

```python
import asyncio

try:
    result = await asyncio.wait_for(
        device.ping_request(timeout=5.0),
        timeout=6.0  # Hard timeout
    )
except asyncio.TimeoutError:
    print("Device timeout")
except Exception as e:
    print(f"Device error: {e}")
finally:
    await device.disconnect()
```

## Timeout Behavior

Each async method accepts a timeout parameter:

```python
# Method timeout (internal)
success = await device.ping_request(timeout=3.0)

# Hard timeout (from calling code)
result = await asyncio.wait_for(
    device.ping_request(timeout=3.0),
    timeout=4.0  # Total 4s max
)
```

The hard timeout should be slightly longer than method timeout to allow protocol overhead.

## Supported Devices

```python
supported = AsyncDeviceFactory.get_supported_devices()
# ['RX11', 'RX11-BASIC', 'RX11-EW', 'RX11-DEV',
#  'RX21', 'RX21-BASIC', 'RX21-EW', 'RX21-DEV',
#  'RX22', 'RX22-BASIC', 'RX22-EW', 'RX22-DEV',
#  'RX25', 'RX25-BASIC', 'RX25-EW', 'RX25-DEV',
#  'RX09', 'RX09-BASIC']
```

## Example: Home Assistant Custom Component

See `examples/ha_integration_example.py` for a complete example including:
- Device setup/teardown pattern
- Health check loop
- Error handling 
- Entity integration pattern

## Performance Notes

- **ThreadPoolExecutor**: Uses 4 worker threads (shared across all devices)
- **No blocking on event loop**: All serial I/O runs in background threads
- **Concurrent devices**: Multiple devices can operate simultaneously
- **Resource cleanup**: Always call `await device.disconnect()` or use context manager

## Debugging

Enable debug logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('easywave_rx_module')
logger.setLevel(logging.DEBUG)
```

## Migration from Sync API

If you have existing code using the synchronous `DeviceFactory`:

```python
# OLD (synchronous - blocks event loop)
from easywave_rx_module import DeviceFactory
device = DeviceFactory.create("RX22", port="/dev/ttyUSB0")
device.ping_request()

# NEW (async - non-blocking)
from easywave_rx_module import AsyncDeviceFactory
device = await AsyncDeviceFactory.create("RX22", port="/dev/ttyUSB0")
await device.ping_request()
```

The async wrapper automatically handles thread pool execution, so you just add `async/await` keywords and use with Home Assistant.

## Backward Compatibility

The synchronous API (`DeviceFactory`) is **still available** for non-HA applications:

```python
# Still works for standalone scripts/CLI tools
from easywave_rx_module import DeviceFactory

device = DeviceFactory.create("RX22", port="/dev/ttyUSB0")
device.ping_request()  # Synchronous call
```

But is **NOT recommended** for Home Assistant integration.
"""
