# EASYWAVE Home Control

Pure Python async/await implementation for controlling EASYWAVE radio modules (RX11, RX21, RX22, RX25, RX09).

Optimized for **Home Assistant integration** with a non-blocking async API and a **codec layer** for typed telegram/state parsing.

## What's New in 0.3.1

- **Dual/quad motor summary fix** — mode 0 reports position (`0–100`) in the same field as activity; `MotorSummaryChannelState.position` is now populated correctly
- Multi-motor summary types exported from `easywave_home_control.codec`
- **71 unit tests**

## What's New in 0.3.0

- **Gateway layer** — `create_gateway()`, `RxModuleGateway` / `EasywaveGateway`, protocol facades (`ew`, `ewb`, `sec`)
- **`EntityKind` taxonomy** — explicit integration device categories per transceiver profile
- **`TransceiverProfile` registry** — capability gating for HA config flows; `register_transceiver_profile()` for successors
- **`Rx09Gateway`** — prepared ASCII Easywave Basic gateway
- **69 unit tests**

## What's New in 0.2.1

- **Sensor codec fix (STH01)** — correct EWneo type mapping and `/100` scaling for temperature and humidity
- **Legacy RX21 format** — optional `SensorPayloadFormat.LEGACY_RX21` for Table 6 sensors (`/10`, swapped type codes)
- **55 unit tests** — including dedicated sensor payload coverage

## What's New in 0.2.0

- **EWB codec** — parse/encode state for all seven neo device types (switch, dimmer, motor, dual/quad variants)
- **Secwave codec** — IRP helpers and parsers for SEC_RCV, SEC_LEARN, SEC_SEND, SEC_REPLY_QUERY (aligned with RX21 spec)
- **Easywave Basic codec** — button-byte encoding and `parse_ew_rcv_ex_result` for EW telegrams
- **Protocol fixes** — corrected Secwave IRP/ICP layouts; spec-accurate RX09 response parsing
- **Examples & tests** — updated HA/coordinator patterns; 45 unit tests

## Features

- **Pure Async/Await** — no blocking calls on the event loop
- **Multi-Family Support** — binary protocol (RX11/21/22/25) + ASCII protocol (RX09)
- **Gateway layer** — connection lifecycle, health, reconnect; recommended integration entry point
- **Codec layer** — typed parse/encode instead of raw byte juggling
- **Clean API** — `create_gateway()` for integrations; `AsyncDeviceFactory` / device `.create()` for low-level access
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

The library separates **protocol transport** (IRP/ICP over serial) from **codec parsing** (state words, telegrams, sensor payloads). For integrations, use **`EasywaveGateway`** for connection lifecycle (compare `enocean_async.Gateway`); use the codec for parse/encode.

### Transceiver profiles (HA capability gating)

Each transceiver model has a **profile** declaring supported protocols and EWB device types.
Home Assistant should read this before offering entity types in config flow:

```python
from easywave_home_control import get_transceiver_profile, create_gateway, GatewayProtocol, EntityKind

profile = get_transceiver_profile("RX11")
for kind in profile.supported_entity_kinds():
    ...  # easywave_transmitter, easywave_receiver, easywave_neo_*, secwave_*

gateway = create_gateway("RX11", GatewayConfig(port="/dev/ttyUSB0"))
```

Register a **future RX11 successor** without library code changes:

```python
from easywave_home_control.gateway import (
    TransceiverFamily,
    TransceiverProfile,
    GatewayProtocol,
    register_transceiver_profile,
)

register_transceiver_profile(TransceiverProfile(
    id="RX11_PRO",
    family=TransceiverFamily.RX_MODULE,
    protocols=frozenset({GatewayProtocol.EW, GatewayProtocol.EWB}),
    ewb_device_types=frozenset({...}),
    usb_ids=frozenset({(0x155A, 0x1015)}),
    usb_discovery=True,
))
```

| Transceiver | Entity kinds |
|-------------|----------------|
| RX11 | all six `EntityKind` values |
| RX21/22/25 | same as RX11 (port required) |
| RX09 | `easywave_transmitter`, `easywave_receiver` only |

### Gateway (recommended for integrations)

`RxModuleGateway` (alias `EasywaveGateway`) supports **RX11, RX21, RX22, RX25** with protocol facades:

| Facade | Protocol | Examples |
|--------|----------|----------|
| `gateway.ew` | Easywave Basic | `send_command`, `receive_ex`, `receive_button`, send loop |
| `gateway.ewb` | EWneo (EWB) | `join_device`, `change_state`, `query_state`, `receive` |
| `gateway.sec` | Secwave | `receive`, `learn`, `send_command_telegram`, storage mgmt |

```python
from easywave_home_control import (
    EasywaveGateway,
    GatewayCallbacks,
    GatewayConfig,
)

gateway = EasywaveGateway(
    GatewayConfig(transceiver_id="RX11", port="/dev/ttyUSB0", auto_listen=True),
    callbacks=GatewayCallbacks(on_telegram=handle_telegram),
)
await gateway.start()

await gateway.ew.send_command(gateway_serial, button=0)
await gateway.ewb.change_state(gw, receiver, device_type, mode, command)
error, telegram = await gateway.sec.receive()

await gateway.stop()
```

For UART modules (RX21/22/25), set `transceiver_id` and `port` (USB discovery is RX11-oriented).

Connection lifecycle (health, reconnect, USB swap) lives in the gateway; Home Assistant wires callbacks to entities only.

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

### DATA sensors (STH01, EWneo)

```python
from easywave_home_control.codec import MeasurementType, SensorPayloadFormat, parse_sensor_payload

payload = parse_sensor_payload(info_data)  # default: SensorPayloadFormat.NEO
if payload.measurement_type == MeasurementType.TEMPERATURE:
    print(payload.temperature_celsius)
elif payload.measurement_type == MeasurementType.HUMIDITY:
    print(payload.humidity_percent)

# Legacy RX21 Table 6 sensors (/10, swapped wire types):
legacy = parse_sensor_payload(info_data, payload_format=SensorPayloadFormat.LEGACY_RX21)
```

ST01/ST02, SH01, SL01, and RTS40 use classic button telegrams, not this 8-byte payload.

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
