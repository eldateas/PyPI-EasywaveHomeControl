# EASYWAVE Home Control

Pure Python async/await implementation for controlling EASYWAVE radio modules (RX11, RX21, RX22, RX25, RX09).

Optimized for **Home Assistant integration** with a non-blocking async API and a **codec layer** for typed telegram/state parsing.

## What's New in 0.2.0

- **EWB codec** — parse/encode state for all seven neo device types (switch, dimmer, motor, dual/quad variants)
- **Secwave codec** — IRP helpers and parsers for SEC_RCV, SEC_LEARN, SEC_SEND, SEC_REPLY_QUERY (aligned with RX21 spec)
- **Easywave Basic codec** — button-byte encoding and `parse_ew_rcv_ex_result` for EW telegrams
- **Protocol fixes** — corrected Secwave IRP/ICP layouts; spec-accurate RX09 response parsing
- **Examples & tests** — updated HA/coordinator patterns; 45 unit tests

## Features

- **Pure Async/Await** — no blocking calls on the event loop
- **Multi-Family Support** — binary protocol (RX11/21/22/25) + ASCII protocol (RX09)
- **Codec Layer** — typed parse/encode instead of raw byte juggling in integrations
- **Robust** — error handling, health checks, timeout management
- **Clean API** — unified `.create()` factory method for all devices
- **Type Hints** — Pylance strict-mode compliant annotations

## Installation

```bash
pip install easywave-home-control
```

## Quick Start

```python
import asyncio
from easywave_home_control import RX11Device, RX11ErrorCode

async def main():
    device = await RX11Device.create(port="/dev/ttyUSB0", timeout=5.0)
    try:
        connected = await device.ping_request(timeout=3.0)
        print(f"Connected: {connected}")

        result, hw_version = await device.query_hw_version()
        if result == RX11ErrorCode.SUCCESS:
            print(f"Hardware: {hw_version}")
    finally:
        await device.disconnect()

asyncio.run(main())
```

## Codec Layer

The library separates **protocol transport** (IRP/ICP over serial) from **codec parsing** (state words, telegrams, sensor payloads). Home Assistant integrations typically keep device mapping and persistence in the integration layer and use the codec for encode/decode.

### Easywave Bidi (EWB neo)

```python
from easywave_home_control import parse_ewb_rcv, parse_ewb_state, encode_ewb_state
from easywave_home_control.codec import StateDirection, SwitchChangeCommand, SwitchDesiredAction
from easywave_home_control.protocols.rx11_rx2x.protocol import DeviceType

# Listen loop (after ewb_rcv_request)
event = parse_ewb_rcv(info_type, serial, info_data, device_type=DeviceType.EWB_DT_SWITCH)

# Query / change state
state = parse_ewb_state(device_type, mode, raw_bytes)
raw = encode_ewb_state(
    device_type, 0,
    SwitchChangeCommand(action=SwitchDesiredAction.ON),
    direction=StateDirection.TO_DEVICE,
)
```

Supported device types: switch, dual/quad switch, dimmer, motor, dual/quad motor.

### Easywave Basic (EW)

```python
from easywave_home_control.codec import easywave, parse_ew_rcv_ex_result

button_byte = easywave.encode_send_button_byte(easywave.EasywaveSendButton.A)
await device.ew_send_cmd_request(gateway_serial, button_byte)

error_code, event = parse_ew_rcv_ex_result(await device.ew_rcv_ex_request())
```

### Secwave

```python
from easywave_home_control import secwave

error_code, telegram = secwave.parse_sec_rcv_result(await device.sec_rcv_request())

params = secwave.encode_sec_send_cmd_tel_params(
    secwave.SecSendCmdTelRequest(
        button_number=0,
        query=secwave.SecQuery(wants_reply=True, reply_only=False),
        command=int(secwave.SecwaveCommand.OPEN),
        flags=secwave.SecTransmitterFlags(mobile=False, low_battery=False),
    )
)
result, primary, secondary = await device.sec_send_cmd_tel_request(params)
response = secwave.parse_sec_send_response(primary, secondary, queried_reply=True)
```

See [examples/](examples/) and [examples/README.md](examples/README.md) for full workflows.

## Device Support

### RxModule Family (Binary Protocol)

| Device | Type | EW | EWB | Secwave | Baudrate |
|--------|------|----|-----|---------|----------|
| **RX11** | USB Transceiver | ✓ | ✓ | ✓ | 115200 |
| **RX21** | Serial Module | ✓ | ✓ | ✓ | 115200 |
| **RX22** | Serial Module | ✓ | ✓ | ✓ | 115200 |
| **RX25** | Serial Module | ✓ | ✓ | ✓ | 115200 |

### RX09 Family (ASCII Protocol, Easywave Basic only)

| Device | Type | Baudrate | Notes |
|--------|------|----------|-------|
| **RX09** | Basic Transceiver | 57600 | Spec-accurate ASCII command parsing |

## Async API

### RxModule Devices

```python
from easywave_home_control import RX11Device, RX11ErrorCode

device = await RX11Device.create(port="/dev/ttyUSB0")

# Easywave Basic
result, info_type, serial, info_data = await device.ew_rcv_ex_request(timeout=30.0)
await device.ew_send_cmd_request(gateway=gateway_serial, button=0)

# Easywave Bidi
result, device_type, receiver = await device.ewb_join_device_request(gateway_serial)
result, mode, state = await device.ewb_query_state_request(gateway, receiver, desired_mode=0)

# Secwave
result, stor_index, *_ = await device.sec_rcv_request(timeout=30.0)
await device.sec_learn_request(user_data=0x00000001, timeout=30.0)
```

### RX09 Device

```python
from easywave_home_control import RX09Device, RX09ErrorCode

device = await RX09Device.create(port="/dev/ttyUSB0")

result, serial_number, button = await device.receive_telegramm(timeout=30.0)
result, num_positions = await device.query_positions()
result = await device.send_telegramm(position=0, button="A")
```

### Common Methods (All Devices)

```python
await device.connect()          # called automatically by .create()
await device.disconnect()
await device.get_device_info()
await device.ping_request(timeout=5.0)
device.is_connected
```

### RxModule Status Properties

```python
device.connection_status   # "connected", "disconnected", "reconnecting", "error", "hardware_error"
device.has_hardware_error
device.state_good
device.last_error
```

## Examples

| Example | Description |
|---------|-------------|
| [ew_send_receive_example.py](examples/ew_send_receive_example.py) | EW gateway discovery, send, receive with codec |
| [ewb_pairing_example.py](examples/ewb_pairing_example.py) | EWB join, query, change, listen |
| [secwave_example.py](examples/secwave_example.py) | Secwave listen, learn, send, reply |
| [ha_integration_full_example.py](examples/ha_integration_full_example.py) | HA coordinator pattern (restore, listen, turn_on) |

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Protocol Details

### RxModule (RX11/21/22/25)

Binary protocol: `[SOP 0x81] [Function + Params] [EOP 0x82]` with byte stuffing, IRP/ICP request/response pairs, and optional indefinite timeouts on receive functions.

### RX09 (RTR09)

ASCII protocol at 57600 8N1: comma-separated commands, `\r` terminator, responses such as `ID,<vendor>,<device>,<version>` and spontaneous `REC,<serial>,<button>`.

## Requirements

- Python 3.9+
- pyserial >= 3.5

## License

Apache License 2.0 — see [LICENSE](LICENSE).

## Contributing

Contributions are welcome! Please submit issues and pull requests to the [Home Assistant repository](https://github.com/home-assistant/core).

## Support

For integration guidance, see the [Home Assistant Easywave Integration](https://www.home-assistant.io/integrations/easywave) documentation.
